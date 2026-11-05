from __future__ import annotations

import logging

from telegram import BusinessMessagesDeleted, Message

from bot.storage import MessageStorage

logger = logging.getLogger(__name__)


def resolve_connection_id(
    storage: MessageStorage,
    *,
    message: Message | None = None,
    deleted: BusinessMessagesDeleted | None = None,
) -> str | None:
    if message and message.business_connection_id:
        return message.business_connection_id
    if deleted and deleted.business_connection_id:
        return deleted.business_connection_id

    chat_id = None
    if message:
        chat_id = message.chat.id
    elif deleted:
        chat_id = deleted.chat.id

    if chat_id is not None:
        mapped = storage.get_chat_connection(chat_id)
        if mapped:
            logger.debug("Using mapped connection for chat %s", chat_id)
            return mapped

    primary = storage.get_primary_connection_id()
    if primary:
        logger.debug("Using primary business connection fallback")
        return primary

    logger.warning("Could not resolve business_connection_id")
    return None
