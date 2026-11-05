from __future__ import annotations

import asyncio
from pathlib import Path
import logging

from telegram import Message
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

DOWNLOAD_TIMEOUT = 120
GET_FILE_TIMEOUT = 30


MEDIA_FIELDS = (
    ("photo", "photo"),
    ("video", "video"),
    ("voice", "voice"),
    ("video_note", "video_note"),
    ("audio", "audio"),
    ("document", "document"),
)


def detect_media_type(message: Message) -> tuple[str | None, str | None, str | None, object | None]:
    if message.photo:
        best = message.photo[-1]
        return "photo", best.file_id, best.file_unique_id, best

    for attr, media_type in MEDIA_FIELDS:
        if attr == "photo":
            continue
        media_object = getattr(message, attr, None)
        if media_object and getattr(media_object, "file_id", None):
            return media_type, media_object.file_id, media_object.file_unique_id, media_object

    return None, None, None, None


async def download_media(
    message: Message,
    context: ContextTypes.DEFAULT_TYPE,
    media_dir: Path,
) -> str | None:
    media_type, file_id, file_unique_id, media_object = detect_media_type(message)
    if not file_id:
        return None

    subdir = media_dir / str(message.chat.id) / (media_type or "other")
    subdir.mkdir(parents=True, exist_ok=True)

    tg_file = None
    if media_object is not None and hasattr(media_object, "get_file"):
        try:
            tg_file = await asyncio.wait_for(
                media_object.get_file(),
                timeout=GET_FILE_TIMEOUT
            )
        except asyncio.TimeoutError:
            logger.warning(
                "media_object.get_file TIMEOUT for message %s media_type %s",
                message.message_id,
                media_type,
            )
            tg_file = None
        except Exception as exc:
            logger.warning(
                "media_object.get_file failed for message %s media_type %s: %s",
                message.message_id,
                media_type,
                exc,
            )
            tg_file = None

    if tg_file is None:
        try:
            tg_file = await asyncio.wait_for(
                context.bot.get_file(file_id),
                timeout=GET_FILE_TIMEOUT
            )
        except asyncio.TimeoutError:
            logger.exception(
                "context.bot.get_file TIMEOUT for message %s media_type %s file_id %s",
                message.message_id,
                media_type,
                file_id,
            )
            raise
        except Exception as exc:
            logger.exception(
                "context.bot.get_file failed for message %s media_type %s file_id %s",
                message.message_id,
                media_type,
                file_id,
            )
            raise

    suffix = _guess_extension(tg_file.file_path, media_type)
    filename = f"{message.message_id}_{file_unique_id}{suffix}"
    local_path = subdir / filename

    try:
        await asyncio.wait_for(
            tg_file.download_to_drive(custom_path=str(local_path)),
            timeout=DOWNLOAD_TIMEOUT
        )
    except asyncio.TimeoutError:
        logger.error(
            "Download TIMEOUT for message %s media_type %s (file size too large or slow connection)",
            message.message_id,
            media_type,
        )
        if local_path.exists():
            try:
                local_path.unlink()
            except Exception as e:
                logger.warning("Failed to remove incomplete file %s: %s", local_path, e)
        raise

    return str(local_path)


def _guess_extension(file_path: str | None, media_type: str | None) -> str:
    if file_path and "." in file_path:
        return "." + file_path.rsplit(".", 1)[-1]
    defaults = {
        "photo": ".jpg",
        "video": ".mp4",
        "voice": ".ogg",
        "video_note": ".mp4",
        "audio": ".mp3",
        "document": ".bin",
    }
    return defaults.get(media_type or "", ".bin")
