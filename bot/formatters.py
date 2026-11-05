from __future__ import annotations

from datetime import datetime
from html import escape

from bot.storage import StoredMessage

_MEDIA_LABELS = {
    "photo": "Фото",
    "voice": "Голосовое",
    "video_note": "Кружок",
    "video": "Видео",
    "document": "Документ",
    "audio": "Аудио",
    "animation": "Анимация",
    "sticker": "Стикер",
}


def _fmt_dt(iso: str | None) -> str:
    if not iso:
        return "—"
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%d.%m.%Y %H:%M:%S")
    except ValueError:
        return escape(iso)


def _fmt_chat_link(chat_title: str | None, chat_id: int) -> str:
    label = escape(chat_title) if chat_title else f"Чат {chat_id}"
    return f'<a href="tg://user?id={chat_id}">{label}</a>'


def _meta_block(
    *,
    chat_link: str,
    date: str | None = None,
    extra_lines: list[str] | None = None,
) -> str:
    lines = [f"💬  {chat_link}"]
    if date:
        lines.append(f"🕐  {date}")
    if extra_lines:
        lines.extend(extra_lines)
    return "\n".join(lines)


def _content_block(label: str, content: str | None) -> str | None:
    if not content:
        return None
    return f"<b>{escape(label)}</b>\n<blockquote>{escape(content)}</blockquote>"


def format_deleted_notification(msg: StoredMessage, chat_title: str | None) -> str:
    parts = ["🗑  <b>Удалено сообщение</b>", ""]
    parts.append(
        _meta_block(
            chat_link=_fmt_chat_link(chat_title, msg.chat_id),
            date=_fmt_dt(msg.date),
        )
    )

    if msg.has_protected_content:
        parts.extend(["", "⚠️  Защищённый / одноразовый контент"])

    if msg.media_type:
        label = _MEDIA_LABELS.get(msg.media_type, "Медиа")
        parts.extend(["", f"📎  {label}"])

    text_block = _content_block("Текст", msg.text)
    if text_block:
        parts.extend(["", text_block])

    caption_block = _content_block("Подпись", msg.caption)
    if caption_block:
        parts.extend(["", caption_block])

    return "\n".join(parts)


def format_saved_reply_media_notification(
    chat_title: str | None,
    chat_id: int,
    media_type: str | None,
) -> str:
    media_label = _MEDIA_LABELS.get(media_type, "Медиа")
    return "\n".join(
        [
            "💾  <b>Сохранено одноразовое медиа</b>",
            "",
            _meta_block(
                chat_link=_fmt_chat_link(chat_title, chat_id),
                extra_lines=[f"📎  {media_label}"],
            ),
        ]
    )


def format_edit_notification(
    chat_title: str | None,
    chat_id: int,
    original_text: str | None,
    original_caption: str | None,
    new_text: str | None,
    new_caption: str | None,
) -> str:
    parts = [
        "✏️  <b>Отредактировано сообщение</b>",
        "",
        _meta_block(chat_link=_fmt_chat_link(chat_title, chat_id)),
    ]

    if original_text is not None or new_text is not None:
        before = _content_block("Было", original_text or "—")
        after = _content_block("Стало", new_text or "—")
        if before:
            parts.extend(["", before])
        if after:
            parts.extend(["", after])

    if original_caption is not None or new_caption is not None:
        before = _content_block("Подпись была", original_caption or "—")
        after = _content_block("Подпись стала", new_caption or "—")
        if before:
            parts.extend(["", before])
        if after:
            parts.extend(["", after])

    return "\n".join(parts)


def format_missing_deleted_notification(
    chat_title: str | None,
    chat_id: int,
) -> str:
    return "\n".join(
        [
            "🗑  <b>Удалены сообщения</b>",
            "<i>Не были сохранены ранее</i>",
            "",
            f"💬  {_fmt_chat_link(chat_title, chat_id)}",
        ]
    )
