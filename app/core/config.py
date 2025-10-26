# app/core/config.py
import os

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


