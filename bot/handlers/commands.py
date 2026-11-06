from __future__ import annotations

from html import escape

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from bot.config import ADMIN_USER_ID
from bot.handlers.notifications import mark_chat_unblocked


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user and context.args and context.args[0].startswith("ref_"):
        referrer_id = context.args[0][4:]
        if referrer_id.isdigit():
            storage = context.application.bot_data["storage"]
            storage.register_referral(user.id, int(referrer_id))

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
            referrer_id = row["referrer_user_id"]
            inviter = (
                f'<a href="tg://user?id={int(referrer_id)}">{int(referrer_id)}</a>'
                if referrer_id is not None
                else "не указан"
            )
            lines.append(f"• {connected_link} · пригласил: {inviter}")
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


def _referral_menu(count: int) -> tuple[str, InlineKeyboardMarkup]:
    progress = min(count, 5)
    buttons = [InlineKeyboardButton("Создать пригласительную ссылку", callback_data="referral:create")]
    if count >= 5:
        buttons.append(InlineKeyboardButton("Забрать приз", callback_data="referral:claim"))
    text = (
        f"Приглашено и подключено: {progress}/5\n"
        "Приглашение засчитывается после подключения Telegram Business."
    )
    return text, InlineKeyboardMarkup([buttons])


async def referral_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.effective_message
    if not user or not message:
        return
    storage = context.application.bot_data["storage"]
    text, keyboard = _referral_menu(storage.get_referral_count(user.id))
    await message.reply_text(text, reply_markup=keyboard)


async def referral_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return

    user_id = query.from_user.id
    storage = context.application.bot_data["storage"]
    if query.data == "referral:create":
        username = context.bot.username
        if not username:
            await query.answer("Не удалось получить имя бота.", show_alert=True)
            return
        link = f"https://t.me/{username}?start=ref_{user_id}"
        await query.answer("Ссылка создана.")
        if query.message:
            await query.message.reply_text(f"Ваша пригласительная ссылка:\n{escape(link)}")
        return

    if query.data == "referral:claim":
        claimed, count = storage.claim_referral_reward(user_id)
        if not claimed:
            await query.answer("Для приза нужно 5 подключённых приглашённых.", show_alert=True)
            return
        await query.answer("Приз отмечен.")
        if query.message:
            await query.message.reply_text(
                "Поздравляем! Вы достигли цели. Подарок в виде мишки будет выдан в ближайшее время."
            )
            text, keyboard = _referral_menu(count)
            await query.edit_message_text(text, reply_markup=keyboard)
