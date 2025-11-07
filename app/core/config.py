# app/core/config.py
import os
from typing import Optional

from dotenv import load_dotenv

# Загружаем переменные окружения из файла .env
# Это позволяет хранить конфигурацию (токены, пути) отдельно от кода.
load_dotenv()


# --- Telegram Bot Token ---
BOT_TOKEN: Optional[str] = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    # Если токен не найден, приложение не может работать.
    # Вызываем критическую ошибку.
    raise RuntimeError(
        "BOT_TOKEN не найден. Проверьте .env файл или переменные окружения."
    )

# --- Gemini API Token ---
GEMINI_TOKEN: Optional[str] = os.getenv("GEMINI_TOKEN")
if not GEMINI_TOKEN:
    raise RuntimeError(
        "GEMINI_TOKEN не найден. Проверьте .env файл или переменные окружения."
    )

# --- Database Configuration ---
DB_NAME: Optional[str] = os.getenv("DB_NAME_SQLITE")
if not DB_NAME:
    raise RuntimeError(
        "DB_NAME_SQLITE не найден. Проверьте .env файл или переменные окружения."
    )

# Формируем URL для подключения к базе данных SQLite через aiosqlite.
DB_URL_SQLALCHEMY: str = f"sqlite+aiosqlite:///{DB_NAME}"

# --- Redis Configuration ---
# Используем значения по умолчанию, если они не заданы в .env
REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6379))
REDIS_PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD")

# Формируем URL для подключения к Redis в зависимости от наличия пароля.
if REDIS_PASSWORD:
    # Формат URL с паролем
    REDIS_URL: str = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}"
else:
    # Формат URL без пароля
    REDIS_URL: str = f"redis://{REDIS_HOST}:{REDIS_PORT}"
