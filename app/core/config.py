# app/core/config.py
import os
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN не найден. Проверьте .env файл или переменные окружения."
    )

GEMINI_TOKEN = os.getenv("GEMINI_TOKEN")
if not GEMINI_TOKEN:
    raise RuntimeError(
        "GEMINI_TOKEN не найден. Проверьте .env файл или переменные окружения."
    )

DB_NAME = os.getenv("DB_NAME_SQLITE")
if not DB_NAME:
    raise RuntimeError(
        "DB_NAME_SQLITE не найден. Проверьте .env файл или переменные окружения."
        )

DB_URL_SQLALCHEMY = f"sqlite+aiosqlite:///{DB_NAME}"

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD")

if REDIS_PASSWORD:
    # Формат с паролем
    REDIS_URL = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}"
else:
    # Формат БЕЗ пароля
    REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}"
