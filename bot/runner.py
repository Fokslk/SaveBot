from __future__ import annotations

import asyncio
import contextlib
import logging
import threading
from pathlib import Path

from telegram import Update
from telegram.error import Conflict, Forbidden, NetworkError, TimedOut
from telegram.ext import (
    Application,
    BusinessConnectionHandler,
    BusinessMessagesDeletedHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    TypeHandler,
    filters,
)

from bot.config import load_config
from bot.handlers.business_connection import handle_business_connection
from bot.handlers.commands import start_command, status_command
from bot.handlers.deleted import handle_deleted_business_messages
from bot.handlers.messages import handle_business_message, handle_edited_business_message
from bot.runtime_stats import STATS
from bot.storage import MessageStorage

logger = logging.getLogger(__name__)


class _FlushedFileHandler(logging.FileHandler):
    def emit(self, record):
        super().emit(record)
        self.flush()


class _PollHeartbeatFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
        except Exception:
            return True
        if "getUpdates" in msg:
            STATS.touch_poll()
            return False
        return True


def setup_logging(*, console: bool = False) -> None:
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_file = Path(__file__).resolve().parent.parent / "bot.log"

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(logging.INFO)

    file_handler = _FlushedFileHandler(str(log_file), mode="a", encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(log_format))
    root.addHandler(file_handler)

    if console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter(log_format))
        root.addHandler(console_handler)

    logging.getLogger("httpx").setLevel(logging.INFO)
    logging.getLogger("httpx").addFilter(_PollHeartbeatFilter())
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("telegram.ext.ExtBot").setLevel(logging.INFO)


async def _log_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    kinds: list[str] = []
    if update.business_message:
        kinds.append("business_message")
    if update.edited_business_message:
        kinds.append("edited_business_message")
    if update.deleted_business_messages:
        kinds.append("deleted_business_messages")
    if update.business_connection:
        kinds.append("business_connection")
        if update.business_connection.is_enabled:
            logger.info("[ON] Business connection ENABLED: %s", update.business_connection.id)
        else:
            logger.warning("[OFF] Business connection DISABLED: %s", update.business_connection.id)
    if update.message:
        kinds.append("message")
    if kinds:
        STATS.note_update(kinds)


async def _on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    error = context.error

    if isinstance(error, Conflict):
        STATS.set_status("conflict")
        STATS.note_error("Conflict: запущен ещё один экземпляр бота")
        logger.error(
            "Conflict: another getUpdates is running. Stop other bot.main / monitor instances."
        )
        return

    if isinstance(error, Forbidden):
        logger.warning("Delivery forbidden: %s", error)
        STATS.note_error("Forbidden: чат недоступен")
        return

    if isinstance(error, (NetworkError, TimedOut)):
        STATS.note_error(f"Сеть: {type(error).__name__}")
        logger.warning("Network issue: %s", error)
        return

    if isinstance(error, Exception):
        STATS.note_error(f"{type(error).__name__}: {error}")
        logger.error(
            "Error while processing update %s: %s",
            getattr(update, "update_id", "unknown") if update is not None else "unknown",
            error,
            exc_info=error,
        )
    else:
        STATS.note_error("unknown error")
        logger.exception("Unhandled error: %s", update, exc_info=error)


class BotRunner:
    pass

    def __init__(self) -> None:
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._stop_event: asyncio.Event | None = None
        self._app: Application | None = None
        self._lock = threading.Lock()

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        with self._lock:
            if self.is_running:
                return
            STATS.reset_session()
            STATS.set_status("starting")
            self._thread = threading.Thread(target=self._thread_main, name="save-mod-bot", daemon=True)
            self._thread.start()

    def stop(self, timeout: float = 12.0) -> bool:
        with self._lock:
            loop = self._loop
            stop_event = self._stop_event
            thread = self._thread

        if loop is not None and stop_event is not None and loop.is_running():
            loop.call_soon_threadsafe(stop_event.set)

        if thread is not None:
            thread.join(timeout=timeout)
            if thread.is_alive():
                logger.error("Bot thread did not stop within %.1f seconds", timeout)
                return False

        STATS.set_status("stopped")
        with self._lock:
            self._thread = None
            self._loop = None
            self._stop_event = None
            self._app = None
        return True

    def _thread_main(self) -> None:
        setup_logging(console=False)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        stop_event = asyncio.Event()

        with self._lock:
            self._loop = loop
            self._stop_event = stop_event

        try:
            loop.run_until_complete(self._async_main(stop_event))
        except Exception as exc:
            STATS.note_error(f"crash: {type(exc).__name__}: {exc}")
            STATS.set_status("stopped")
            logger.exception("Bot thread crashed")
        finally:
            try:
                pending = asyncio.all_tasks(loop)
                for task in pending:
                    task.cancel()
                if pending:
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            except Exception:
                pass
            loop.close()
            STATS.set_status("stopped")

    async def _async_main(self, stop_event: asyncio.Event) -> None:
        config = load_config()
        storage = MessageStorage(config.database_path)
        total, deleted = storage.count_totals()
        STATS.set_db_totals(total, deleted)

        application = (
            Application.builder()
            .token(config.bot_token)
            .build()
        )
        application.bot_data["config"] = config
        application.bot_data["storage"] = storage

        application.add_handler(TypeHandler(Update, _log_update), group=-1)
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("status", status_command))
        application.add_handler(BusinessConnectionHandler(handle_business_connection))
        application.add_handler(
            MessageHandler(
                filters.UpdateType.BUSINESS_MESSAGE | filters.UpdateType.MESSAGE,
                handle_business_message,
            )
        )
        application.add_handler(
            MessageHandler(
                filters.UpdateType.EDITED_BUSINESS_MESSAGE | filters.UpdateType.EDITED_MESSAGE,
                handle_edited_business_message,
            )
        )
        application.add_handler(BusinessMessagesDeletedHandler(handle_deleted_business_messages))
        application.add_error_handler(_on_error)

        self._app = application

        await application.initialize()

        webhook = await application.bot.get_webhook_info()
        if webhook.url:
            logger.warning("Webhook was active (%s), removing for polling mode", webhook.url)
            await application.bot.delete_webhook(drop_pending_updates=False)

        await application.start()
        await application.updater.start_polling(
            allowed_updates=[
                "message",
                "business_connection",
                "business_message",
                "edited_business_message",
                "deleted_business_messages",
            ],
            drop_pending_updates=False,
        )
        STATS.set_status("online")
        logger.info("Save Mod online — db messages=%s deleted=%s", total, deleted)

        refresh_task = asyncio.create_task(self._refresh_db_loop(storage, stop_event))
        try:
            await stop_event.wait()
        finally:
            refresh_task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await refresh_task
            logger.info("Stopping bot…")
            with contextlib.suppress(Exception):
                await application.updater.stop()
            with contextlib.suppress(Exception):
                await application.stop()
            with contextlib.suppress(Exception):
                await application.shutdown()
            STATS.set_status("stopped")
            logger.info("Bot stopped cleanly")

    async def _refresh_db_loop(self, storage: MessageStorage, stop_event: asyncio.Event) -> None:
        while not stop_event.is_set():
            try:
                total, deleted = storage.count_totals()
                STATS.set_db_totals(total, deleted)
            except Exception:
                logger.exception("db totals refresh failed")
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=15)
            except asyncio.TimeoutError:
                continue
