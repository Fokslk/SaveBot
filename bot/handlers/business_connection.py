from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

from bot.config import ADMIN_USER_ID
from bot.handlers.notifications import mark_chat_unblocked, safe_send
from bot.runtime_stats import STATS

logger = logging.getLogger(__name__)


async def handle_business_connection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    conn = update.business_connection
    if not conn:
        return

    storage = context.application.bot_data["storage"]
    storage.upsert_connection(
        connection_id=conn.id,
        user_id=conn.user.id,
        user_chat_id=conn.user_chat_id,
        is_enabled=conn.is_enabled,
    )

    STATS.note_connection(conn.is_enabled)

    if conn.is_enabled:
        credited = storage.credit_referral(conn.user.id)
        if credited:
            referrer_id, referral_count = credited
            if ADMIN_USER_ID is not None and referral_count % 5 == 0:
                await safe_send(
                    context,
                    ADMIN_USER_ID,
                    kind="message",
                    text=(
                        f'Пользователь <a href="tg://user?id={referrer_id}">{referrer_id}</a> '
                        "набрал 5 подключённых приглашений."
                    ),
                    parse_mode="HTML",
                )
        mark_chat_unblocked(context, conn.user_chat_id)
        text = (
            "✅ <b>Подключение активировано</b>\n\n"
            "Бот начнёт сохранять вам личные переписки. "
            "Уведомления об удалениях и правках будут приходить сюда."
        )
        await safe_send(
            context,
            conn.user_chat_id,
            kind="message",
            text=text,
            parse_mode="HTML",
        )
        logger.info("Business connection enabled: %s (user %s)", conn.id, conn.user.id)
    else:
        await safe_send(
            context,
            conn.user_chat_id,
            kind="message",
            text="⛔ Подключение отключено. Сохранение остановлено.",
        )
        logger.info("Business connection disabled: %s", conn.id)
