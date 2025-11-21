# app/core/config.py
"""
Модуль конфигурации.

Этот файл отвечает за загрузку и предоставление всех конфигурационных
переменных, необходимых для работы приложения. Он использует библиотеку
python-dotenv для загрузки переменных из файла `.env`, что позволяет
гибко настраивать приложение без изменения кода.

Основные задачи:
- Загрузка переменных окружения.
- Проверка наличия критически важных переменных (например, токенов).
- Формирование URL для подключения к базам данных (SQLite, Redis).

При отсутствии обязательных переменных модуль вызывает `RuntimeError`,
предотвращая запуск приложения с неполной конфигурацией.
"""

import os

from dotenv import load_dotenv
from loguru import logger as log

# Инициализируем логгер до того, как что-то может пойти не так.

# Загружаем переменные окружения из файла .env в корне проекта.
# Это должно быть одним из первых действий при запуске приложения.
log.debug("Загрузка переменных окружения из .env файла...")
load_dotenv()
log.debug(".env файл успешно загружен.")

# --- Telegram Bot Token ---
# Критически важная переменная для подключения к API Telegram.
BOT_TOKEN: str | None = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    log.critical("Переменная окружения BOT_TOKEN не найдена!")
    raise RuntimeError("BOT_TOKEN не найден. Проверьте .env файл или переменные окружения.")
log.info("BOT_TOKEN успешно загружен.")

# --- Gemini API Token ---
# Токен для доступа к API генеративной модели Gemini.
GEMINI_TOKEN: str | None = os.getenv("GEMINI_TOKEN")
if not GEMINI_TOKEN:
    log.critical("Переменная окружения GEMINI_TOKEN не найдена!")
    raise RuntimeError("GEMINI_TOKEN не найден. Проверьте .env файл или переменные окружения.")
log.info("GEMINI_TOKEN успешно загружен.")

# --- Database Configuration ---
# Имя файла базы данных SQLite.
DB_NAME: str | None = os.getenv("DB_NAME_SQLITE")
if not DB_NAME:
    log.critical("Переменная окружения DB_NAME_SQLITE не найдена!")
    raise RuntimeError("DB_NAME_SQLITE не найден. Проверьте .env файл или переменные окружения.")

# Формируем URL для подключения к базе данных SQLite через SQLAlchemy.
# Формат: 'dialect+driver://path'
DB_URL_SQLALCHEMY: str = f"sqlite+aiosqlite:///{DB_NAME}"
log.info(f"Сформирован URL для подключения к SQLite: {DB_URL_SQLALCHEMY}")

# --- Redis Configuration ---
# Настройки для подключения к Redis, который используется для FSM (Finite State Machine).
# Используем значения по умолчанию ('localhost', 6379), если они не заданы в .env.
REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6379))
REDIS_PASSWORD: str | None = os.getenv("REDIS_PASSWORD")

# Формируем URL для подключения к Redis в зависимости от наличия пароля.
redis_url_value: str
if REDIS_PASSWORD:
    # Формат URL с паролем
    redis_url_value = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}"
    log.info(f"Сформирован URL для Redis с паролем: redis://:***@{REDIS_HOST}:{REDIS_PORT}")
else:
    # Формат URL без пароля
    redis_url_value = f"redis://{REDIS_HOST}:{REDIS_PORT}"
    log.info(f"Сформирован URL для Redis без пароля: {redis_url_value}")
REDIS_URL: str = redis_url_value

bug_report_channel_id_str = os.getenv("BUG_REPORT_CHANNEL_ID")
BUG_REPORT_CHANNEL_ID: int | None = int(bug_report_channel_id_str) if bug_report_channel_id_str else None


SYSTEM_USER_ID = 2_000_000_000
SYSTEM_CHAR_ID = 2_000_000_000
