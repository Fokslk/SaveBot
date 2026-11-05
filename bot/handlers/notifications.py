from __future__ import annotations

import logging
from pathlib import Path

from telegram import InputFile
from telegram.error import Forbidden, TelegramError
from telegram.ext import ContextTypes

from bot.formatters import (
    format_deleted_notification,
    format_edit_notification,
    format_saved_reply_media_notification,
)
from bot.storage import StoredMessage

logger = logging.getLogger(__name__)

_BLOCKED_KEY = "blocked_chats"


def _blocked_chats(context: ContextTypes.DEFAULT_TYPE) -> set[int]:
    chats = context.application.bot_data.get(_BLOCKED_KEY)
    if chats is None:
        chats = set()
        context.application.bot_data[_BLOCKED_KEY] = chats
    return chats


def mark_chat_unblocked(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    _blocked_chats(context).discard(chat_id)


def _is_blocked_error(exc: BaseException) -> bool:
    if isinstance(exc, Forbidden):
        return True
    if isinstance(exc, TelegramError):
        text = str(exc).lower()
        return any(
            marker in text
            for marker in (
                "blocked by the user",
                "user is deactivated",
                "chat not found",
                "bot can't initiate conversation",
                "have no rights to send",
                "forbidden",
            )
        )
    return False


async def safe_send(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    *,
    kind: str = "message",
    **kwargs,
) -> bool:
    blocked = _blocked_chats(context)
    if chat_id in blocked:
        logger.debug("Skip %s to blocked chat %s", kind, chat_id)
        return False

    try:
        method = {
            "message": context.bot.send_message,
            "photo": context.bot.send_photo,
            "video": context.bot.send_video,
            "voice": context.bot.send_voice,
            "video_note": context.bot.send_video_note,
            "audio": context.bot.send_audio,
            "document": context.bot.send_document,
        }.get(kind, context.bot.send_message)
        await method(chat_id=chat_id, **kwargs)
        return True
    except Exception as exc:
        if _is_blocked_error(exc):
            blocked.add(chat_id)
            logger.warning(
                "Cannot deliver to chat %s (%s) — user blocked the bot or chat is unreachable",
                chat_id,
                type(exc).__name__,
            )
            return False
        logger.exception("Failed to send %s to chat %s", kind, chat_id)
        return False


def resolve_service_chat_id(context: ContextTypes.DEFAULT_TYPE, business_connection_id: str) -> int | None:
    config = context.application.bot_data["config"]
    if config.service_chat_id:
        return config.service_chat_id

    storage = context.application.bot_data["storage"]
    conn = storage.get_connection(business_connection_id)
    if conn:
        return conn["user_chat_id"]
    return None


_CAPTION_LIMIT = 1024


async def notify_deleted(
    context: ContextTypes.DEFAULT_TYPE,
    msg: StoredMessage,
    chat_title: str | None,
) -> None:
    chat_id = resolve_service_chat_id(context, msg.business_connection_id)
    if not chat_id:
        return

    text = format_deleted_notification(msg, chat_title)

    if msg.local_path and Path(msg.local_path).exists():
        if msg.media_type == "video_note" or len(text) > _CAPTION_LIMIT:
            await safe_send(context, chat_id, kind="message", text=text, parse_mode="HTML")
            await _send_saved_file(context, chat_id, msg)
        else:
            await _send_saved_file(context, chat_id, msg, caption=text, parse_mode="HTML")
    else:
        await safe_send(context, chat_id, kind="message", text=text, parse_mode="HTML")


async def notify_saved_reply_media(
    context: ContextTypes.DEFAULT_TYPE,
    business_connection_id: str,
    chat_title: str | None,
    msg: StoredMessage,
) -> None:
    chat_id = resolve_service_chat_id(context, business_connection_id)
    if not chat_id:
        return

    text = format_saved_reply_media_notification(
        chat_title=chat_title,
        chat_id=msg.chat_id,
        media_type=msg.media_type,
    )
    if msg.local_path and Path(msg.local_path).exists():
        if msg.media_type == "video_note" or len(text) > _CAPTION_LIMIT:
            await safe_send(context, chat_id, kind="message", text=text, parse_mode="HTML")
            await _send_saved_file(context, chat_id, msg)
        else:
            await _send_saved_file(context, chat_id, msg, caption=text, parse_mode="HTML")
    else:
        await safe_send(context, chat_id, kind="message", text=text, parse_mode="HTML")


async def notify_edit(
    context: ContextTypes.DEFAULT_TYPE,
    business_connection_id: str,
    chat_title: str | None,
    event_chat_id: int,
    original_text: str | None,
    original_caption: str | None,
    new_text: str | None,
    new_caption: str | None,
) -> None:
    chat_id = resolve_service_chat_id(context, business_connection_id)
    if not chat_id:
        return

    text = format_edit_notification(
        chat_title=chat_title,
        chat_id=event_chat_id,
        original_text=original_text,
        original_caption=original_caption,
        new_text=new_text,
        new_caption=new_caption,
    )
    await safe_send(context, chat_id, kind="message", text=text, parse_mode="HTML")


async def _send_saved_file(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    msg: StoredMessage,
    caption: str | None = None,
    *,
    parse_mode: str | None = None,
) -> None:
    path = Path(msg.local_path)
    media_type = msg.media_type or "document"

    if chat_id in _blocked_chats(context):
        logger.debug("Skip media to blocked chat %s", chat_id)
        return

    try:
        send_kwargs: dict = {}
        if caption and media_type != "video_note":
            send_kwargs["caption"] = caption
            send_kwargs["parse_mode"] = parse_mode

        with path.open("rb") as file_handle:
            file = InputFile(file_handle, filename=path.name)
            if media_type == "photo":
                ok = await safe_send(context, chat_id, kind="photo", photo=file, **send_kwargs)
            elif media_type == "video":
                ok = await safe_send(context, chat_id, kind="video", video=file, **send_kwargs)
            elif media_type == "voice":
                ok = await safe_send(context, chat_id, kind="voice", voice=file, **send_kwargs)
            elif media_type == "video_note":
                ok = await safe_send(context, chat_id, kind="video_note", video_note=file)
            elif media_type == "audio":
                ok = await safe_send(context, chat_id, kind="audio", audio=file, **send_kwargs)
            else:
                ok = await safe_send(context, chat_id, kind="document", document=file, **send_kwargs)

        if not ok:
            return
    except Exception as exc:
        if _is_blocked_error(exc):
            _blocked_chats(context).add(chat_id)
            logger.warning(
                "Cannot deliver media to chat %s — user blocked the bot",
                chat_id,
            )
            return
        logger.exception("Failed to send saved media to service chat")
