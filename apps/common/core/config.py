"""
Модуль конфигурации приложения.

Загружает и предоставляет переменные окружения из `.env` файла.
Проверяет наличие критически важных переменных и формирует URL
для подключения к базам данных (SQLite, Redis).

При отсутствии обязательных переменных вызывает `RuntimeError`,
предотвращая запуск с неполной конфигурацией.
"""

import os

from dotenv import load_dotenv
from loguru import logger as log

log.debug("EnvLoad | status=started")
load_dotenv()
log.debug("EnvLoad | status=success")

# --- Telegram Bot Token ---
# Критически важная переменная для подключения к API Telegram.
BOT_TOKEN: str | None = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    log.critical("ConfigError | reason=missing_env_var var=BOT_TOKEN")
    raise RuntimeError("BOT_TOKEN не найден. Проверьте .env файл или переменные окружения.")
log.info("ConfigLoad | var=BOT_TOKEN status=success")

# --- Gemini API Token ---
# Токен для доступа к API генеративной модели Gemini.
GEMINI_TOKEN: str | None = os.getenv("GEMINI_TOKEN")
if not GEMINI_TOKEN:
    log.critical("ConfigError | reason=missing_env_var var=GEMINI_TOKEN")
    raise RuntimeError("GEMINI_TOKEN не найден. Проверьте .env файл или переменные окружения.")
log.info("ConfigLoad | var=GEMINI_TOKEN status=success")

# --- Database Configuration ---
DB_NAME: str | None = os.getenv("DB_NAME_SQLITE")
if not DB_NAME:
    log.critical("ConfigError | reason=missing_env_var var=DB_NAME_SQLITE")
    raise RuntimeError("DB_NAME_SQLITE не найден. Проверьте .env файл или переменные окружения.")

# Формат: 'dialect+driver://path'
DB_URL_SQLALCHEMY: str = f"sqlite+aiosqlite:///{DB_NAME}"
log.info(f"DatabaseURL | type=sqlite url={DB_URL_SQLALCHEMY}")

# --- Redis Configuration ---
# Настройки для Redis, используемого для FSM.
# Используются значения по умолчанию ('localhost', 6379), если они не заданы.
REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6379))
REDIS_PASSWORD: str | None = os.getenv("REDIS_PASSWORD")

redis_url_value: str
if REDIS_PASSWORD:
    redis_url_value = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}"
    log.info(f"DatabaseURL | type=redis has_password=true url=redis://:***@{REDIS_HOST}:{REDIS_PORT}")
else:
    redis_url_value = f"redis://{REDIS_HOST}:{REDIS_PORT}"
    log.info(f"DatabaseURL | type=redis has_password=false url={redis_url_value}")
REDIS_URL: str = redis_url_value

# --- Channel and User IDs ---
bug_report_channel_id_str = os.getenv("BUG_REPORT_CHANNEL_ID")
BUG_REPORT_CHANNEL_ID: int | None = int(bug_report_channel_id_str) if bug_report_channel_id_str else None

SYSTEM_USER_ID = 2_000_000_000
SYSTEM_CHAR_ID = SYSTEM_USER_ID

# --- Admin Configuration ---
# TODO: Рассмотреть использование Pydantic для более надежной валидации конфигурации.
admin_ids_str = os.getenv("ADMIN_IDS", "")
ADMIN_IDS: list[int] = []
if admin_ids_str:
    try:
        ADMIN_IDS = [int(s) for s in (x.strip() for x in admin_ids_str.split(",")) if s]
        log.info(f"AdminConfig | count={len(ADMIN_IDS)} status=loaded")
    except ValueError:
        log.error("AdminConfig | status=parse_error reason='Invalid format in .env'", exc_info=True)
else:
    log.warning("AdminConfig | status=not_set message='Admin panel will be unavailable'")
