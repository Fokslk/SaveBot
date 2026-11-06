from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from bot.config import ADMIN_USER_ID
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
    user = update.effective_user
    if ADMIN_USER_ID is None:
        if update.effective_message:
            await update.effective_message.reply_text(
                "Администратор не настроен. Заполните ADMIN_USER_ID в bot/config.py."
            )
        return
    if not user or user.id != ADMIN_USER_ID:
        if update.effective_message:
            await update.effective_message.reply_text("Эта команда доступна только администратору.")
        return
    chat = update.effective_chat
    if not chat or chat.type != "private":
        if update.effective_message:
            await update.effective_message.reply_text("Используйте эту команду в личном чате с ботом.")
        return

    storage = context.application.bot_data["storage"]
    rows = storage.get_active_connections()
    if not rows:
        text = "Активных подключений пока нет."
    else:
        lines = ["<b>Активные подключения</b>"]
        for row in rows:
            connected_id = int(row["user_id"])
            connected_link = f'<a href="tg://user?id={connected_id}">{connected_id}</a>'
            lines.append(f"• {connected_link} · подключено: {row['updated_at']}")
        text = "\n".join(lines)

    message = update.effective_message
    if message:
        current = ""
        for line in text.splitlines():
            candidate = f"{current}\n{line}" if current else line
            if len(candidate) > 3800 and current:
                await message.reply_text(current, parse_mode="HTML")
                current = line
            else:
                current = candidate
        if current:
            await message.reply_text(current, parse_mode="HTML")
