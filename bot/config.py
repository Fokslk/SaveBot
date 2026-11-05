from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(override=True)

BASE_DIR = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Config:
    bot_token: str
    service_chat_id: int | None
    database_path: Path
    media_dir: Path


BASE_DIR = Path(__file__).resolve().parent.parent

_PLACEHOLDER_TOKENS = {
    "123456789:ABCdefGHIjklMNOpqrsTUVwxyz",
    "your_bot_token_here",
    "123:ABC",
}


def _validate_token(token: str) -> None:
    if token in _PLACEHOLDER_TOKENS or token.startswith("123456789:"):
        raise RuntimeError(
            "BOT_TOKEN содержит пример из .env.example.\n"
            "Получите настоящий токен у @BotFather (/newbot) и вставьте его в файл .env"
        )
    if ":" not in token or len(token) < 20:
        raise RuntimeError(
            "BOT_TOKEN выглядит некорректно.\n"
            "Токен должен быть вида 1234567890:AAH... (получите у @BotFather)"
        )


def load_config() -> Config:
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("BOT_TOKEN не задан. Скопируйте .env.example в .env и укажите токен.")

    _validate_token(token)

    service_chat_raw = os.getenv("SERVICE_CHAT_ID", "").strip()
    service_chat_id = int(service_chat_raw) if service_chat_raw else None

    database_path = BASE_DIR / os.getenv("DATABASE_PATH", "data/messages.db")
    media_dir = BASE_DIR / os.getenv("MEDIA_DIR", "media")

    database_path.parent.mkdir(parents=True, exist_ok=True)
    media_dir.mkdir(parents=True, exist_ok=True)

    return Config(
        bot_token=token,
        service_chat_id=service_chat_id,
        database_path=database_path,
        media_dir=media_dir,
    )
