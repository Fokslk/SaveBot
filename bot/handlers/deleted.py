from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes

from bot.handlers.notifications import notify_deleted
from bot.runtime_stats import STATS
from bot.utils import resolve_connection_id

logger = logging.getLogger(__name__)


async def handle_deleted_business_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    deleted = update.deleted_business_messages
    if not deleted:
        return

    storage = context.application.bot_data["storage"]
    chat_id = deleted.chat.id
    connection_id = resolve_connection_id(storage, deleted=deleted)
    if not connection_id:
        logger.error("Delete event without connection id: chat=%s ids=%s", chat_id, deleted.message_ids)
        return

    storage.bind_chat_connection(chat_id, connection_id)
    chat_title = deleted.chat.full_name or deleted.chat.username

    logger.info(
        "Delete event in chat %s (%s): ids=%s",
        chat_id,
        chat_title,
        deleted.message_ids,
    )

    stored_messages = storage.mark_deleted(
        message_ids=list(deleted.message_ids),
        chat_id=chat_id,
        business_connection_id=connection_id,
    )
    STATS.note_deleted(len(deleted.message_ids))

    for msg in stored_messages:
        await notify_deleted(context, msg, chat_title)

    for msg in stored_messages:
        if msg.text and not msg.media_type:
            _save_deleted_text_message(context, msg)

    missing_ids = set(deleted.message_ids) - {m.message_id for m in stored_messages}
    if missing_ids:
        logger.warning(
            "Deleted messages without prior log: chat=%s ids=%s",
            chat_id,
            sorted(missing_ids),
        )
        from bot.formatters import format_missing_deleted_notification
        from bot.handlers.notifications import resolve_service_chat_id, safe_send

        service_chat = resolve_service_chat_id(context, connection_id)
        if service_chat:
            await safe_send(
                context,
                service_chat,
                kind="message",
                text=format_missing_deleted_notification(chat_title, chat_id),
                parse_mode="HTML",
            )


def _save_deleted_text_message(context: ContextTypes.DEFAULT_TYPE, msg) -> None:
    config = context.application.bot_data["config"]
    user_folder = config.media_dir / str(msg.chat_id)
    user_folder.mkdir(parents=True, exist_ok=True)
    text_file = user_folder / "deleted_texts.txt"

    now = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    with text_file.open("a", encoding="utf-8") as file:
        file.write(
            f"[{now}] message_id={msg.message_id} from={msg.from_user_name or msg.from_user_id}\n"
        )
        file.write(f"{msg.text or ''}\n")
        file.write("---\n")
