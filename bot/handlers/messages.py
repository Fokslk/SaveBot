from __future__ import annotations

import logging
from datetime import datetime, timezone

from telegram import Message, Update
from telegram.ext import ContextTypes

from bot.media import detect_media_type, download_media
from bot.runtime_stats import STATS
from bot.storage import MessageStorage
from bot.utils import resolve_connection_id

logger = logging.getLogger(__name__)


def _user_display(message: Message) -> tuple[int | None, str | None, str | None]:
    user = message.from_user
    if not user:
        return None, None, None
    name = user.full_name or None
    username = user.username or None
    return user.id, name, username


def _to_iso(value: datetime | int | float | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()


_ONE_TIME_MEDIA_TYPES = frozenset({"photo", "video", "video_note"})


def _is_one_time_media(message: Message, media_type: str | None) -> bool:
    return bool(media_type in _ONE_TIME_MEDIA_TYPES and message.has_protected_content)


async def _save_replied_ephemeral_media(message: Message, context: ContextTypes.DEFAULT_TYPE) -> None:
    reply = message.reply_to_message
    if not reply:
        return

    media_type, file_id, _, _ = detect_media_type(reply)
    if not file_id or not _is_one_time_media(reply, media_type):
        return

    storage: MessageStorage = context.application.bot_data["storage"]
    connection_id = resolve_connection_id(storage, message=reply)
    if not connection_id:
        logger.debug(
            "Reply-to media skipped because no business_connection_id: %s",
            reply.message_id,
        )
        return

    connection = storage.get_connection(connection_id)
    replier_id = message.from_user.id if message.from_user else None
    if not connection or not replier_id or replier_id != connection["user_id"]:
        logger.debug(
            "Skip one-time media notify: reply is not from business owner (msg=%s)",
            reply.message_id,
        )
        return

    existing = storage.get_message(reply.message_id, reply.chat.id, connection_id)
    if not (existing and existing.local_path):
        logger.info(
            "Saving replied one-time media %s (%s) from chat %s",
            reply.message_id,
            media_type,
            reply.chat.id,
        )
        try:
            await _persist_message(reply, context, is_edit=False)
        except Exception:
            logger.exception("Failed to persist replied ephemeral media %s", reply.message_id)
            return

    stored = storage.get_message(reply.message_id, reply.chat.id, connection_id)
    if not stored:
        return

    from bot.handlers.notifications import notify_saved_reply_media

    chat_title = reply.chat.full_name or reply.chat.username
    await notify_saved_reply_media(
        context=context,
        business_connection_id=connection_id,
        chat_title=chat_title,
        msg=stored,
    )


async def _persist_message(
    message: Message,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    is_edit: bool = False,
) -> None:
    storage: MessageStorage = context.application.bot_data["storage"]
    config = context.application.bot_data["config"]

    connection_id = resolve_connection_id(storage, message=message)
    if not connection_id:
        logger.error(
            "Skip message %s: no business_connection_id (chat=%s)",
            message.message_id,
            message.chat.id,
        )
        return

    storage.bind_chat_connection(message.chat.id, connection_id)

    media_type, file_id, file_unique_id, _ = detect_media_type(message)
    local_path = None

    if file_id:
        try:
            local_path = await download_media(message, context, config.media_dir)
            logger.info(
                "Downloaded %s for message %s (chat %s)%s: %s",
                media_type or "media",
                message.message_id,
                message.chat.id,
                " [one-time]" if _is_one_time_media(message, media_type) else "",
                local_path,
            )
        except Exception:
            logger.exception("Failed to download media for message %s", message.message_id)
    from_user_id, from_user_name, from_username = _user_display(message)
    date_iso = _to_iso(message.date) or datetime.now(timezone.utc).isoformat()
    edit_date_iso = _to_iso(message.edit_date)

    existing = storage.get_message(message.message_id, message.chat.id, connection_id)

    if is_edit and existing:
        storage.save_edit(
            message_id=message.message_id,
            chat_id=message.chat.id,
            business_connection_id=connection_id,
            original_text=existing.text,
            original_caption=existing.caption,
            new_text=message.text,
            new_caption=message.caption,
        )

    storage.save_message(
        {
            "message_id": message.message_id,
            "chat_id": message.chat.id,
            "business_connection_id": connection_id,
            "from_user_id": from_user_id,
            "from_user_name": from_user_name or (f"@{from_username}" if from_username else None),
            "text": message.text,
            "caption": message.caption,
            "media_type": media_type,
            "file_id": file_id,
            "file_unique_id": file_unique_id,
            "local_path": local_path,
            "has_protected_content": bool(message.has_protected_content),
            "date": existing.date if existing else date_iso,
            "edit_date": edit_date_iso,
            "raw_json": MessageStorage.message_to_json(message),
        }
    )

    preview = (message.text or message.caption or media_type or "empty")[:80]
    logger.info(
        "Saved business message %s from chat %s (%s): %r",
        message.message_id,
        message.chat.id,
        from_user_name or from_username,
        preview,
    )
    if is_edit:
        STATS.note_edit()
    else:
        STATS.note_message(
            user_id=from_user_id,
            chat_id=message.chat.id,
            name=from_user_name,
            username=from_username,
            text=message.text or message.caption or "",
            media_type=media_type,
            is_one_time=_is_one_time_media(message, media_type),
        )
        if file_id:
            STATS.note_media(media_type)


async def handle_business_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.business_message or update.message
    if not message:
        return

    try:
        await _save_replied_ephemeral_media(message, context)
    except Exception:
        logger.exception("Failed to save replied ephemeral media for message %s", message.message_id)

    try:
        await _persist_message(message, context, is_edit=False)
    except Exception:
        logger.exception("Failed to persist business message %s", message.message_id)


async def handle_edited_business_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.edited_business_message or getattr(update, 'edited_message', None)
    if not message:
        return

    storage: MessageStorage = context.application.bot_data["storage"]
    connection_id = resolve_connection_id(storage, message=message)
    if not connection_id:
        return

    existing = storage.get_message(message.message_id, message.chat.id, connection_id)
    original_text = existing.text if existing else None
    original_caption = existing.caption if existing else None

    try:
        await _persist_message(message, context, is_edit=True)
    except Exception:
        logger.exception("Failed to persist edited business message %s", message.message_id)
        return

    from bot.handlers.notifications import notify_edit

    chat_title = message.chat.full_name or message.chat.username

    await notify_edit(
        context=context,
        business_connection_id=connection_id,
        chat_title=chat_title,
        event_chat_id=message.chat.id,
        original_text=original_text,
        original_caption=original_caption,
        new_text=message.text,
        new_caption=message.caption,
    )
