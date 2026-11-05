from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from bot.handlers.notifications import mark_chat_unblocked


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "👋 <b>Save Mod — чат-бот для сохранения переписок</b>\n\n"
        "Этот бот предназначен для работы через <b>Чат-боты</b>. "
        "Он перехватывает события в личных диалогах и сохраняет:\n"
        "• удалённые сообщения\n"
        "• историю редактирования\n"
        "• одноразовые фото, видео и кружки (только если вы на них ответите)\n"
        "<b>Подключение:</b>\n"
        "1. Скопируйте @username этого бота\n"
        "2. Откройте Настройки → Telegram для бизнеса → Чат-боты\n"
        "3. Вставьте @SaveBotSMS_bot и выдайте права на чтение сообщений\n\n"
        "После подключения уведомления будут приходить в этот чат."
    )
    if update.message:
        mark_chat_unblocked(context, update.message.chat_id)
        await update.message.reply_text(text, parse_mode="HTML")


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    storage = context.application.bot_data["storage"]
    connections = []

    with storage._connect() as conn:
        rows = conn.execute(
            "SELECT id, user_id, is_enabled, updated_at FROM business_connections ORDER BY updated_at DESC"
        ).fetchall()

    if not rows:
        text = "❌ Подключения не найдены. Подключите бота через Чат-боты."
    else:
        lines = ["📊 <b>Статус подключений</b>\n"]
        for row in rows:
            status = "✅ активно" if row["is_enabled"] else "⛔ отключено"
            lines.append(f"• {status} — user {row['user_id']} ({row['updated_at']})")
        text = "\n".join(lines)

    if update.message:
        await update.message.reply_text(text, parse_mode="HTML")
