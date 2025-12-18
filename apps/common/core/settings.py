from pathlib import Path

from loguru import logger as log
from pydantic_settings import BaseSettings, SettingsConfigDict

# Определяем корень проекта
# settings.py -> core -> common -> apps -> ROOT
ROOT_DIR = Path(__file__).parent.parent.parent.parent
ENV_FILE_PATH = ROOT_DIR / ".env"


class Settings(BaseSettings):
    # --- БЛОК 0: Токены (Критичные данные) ---
    # Если их нет в .env, приложение упадет с ошибкой (валидация Pydantic)
    bot_token: str
    gemini_token: str

    # --- БЛОК 1: Redis ---
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str | None = None
    redis_max_connections: int = 50
    redis_timeout: int = 5

    # --- БЛОК 2: База Данных ---
    database_url: str  # Убрали дефолт, теперь URL обязателен в .env
    # Флаг для SSL подключения к БД (True для Neon/Cloud, False для локального Docker)
    db_ssl_require: bool = True

    # --- БЛОК 3: Логирование ---
    log_level_console: str = "DEBUG"
    log_level_file: str = "DEBUG"
    log_rotation: str = "10 MB"
    log_dir: str = "logs"

    # --- БЛОК 4: Игровые настройки и Каналы (Перенесли из config.py) ---
    bug_report_channel_id: int | None = None

    # Список админов. В .env пишем: ADMIN_IDS=12345,67890
    admin_ids: str = ""

    # Системные константы (Hardcoded values)
    system_user_id: int = 2_000_000_000

    # Таймаут для поиска матча на арене в секундах
    arena_matchmaking_timeout: int = 30

    @property
    def system_char_id(self) -> int:
        return self.system_user_id

    # --- Свойства и Валидаторы ---

    @property
    def admin_ids_list(self) -> list[int]:
        """Парсит строку '123,456' в список чисел."""
        if not self.admin_ids:
            return []
        try:
            return [int(x.strip()) for x in self.admin_ids.split(",") if x.strip()]
        except ValueError:
            log.warning(f"Settings | Failed to parse ADMIN_IDS='{self.admin_ids}'. Check .env format.")
            return []

    @property
    def redis_url(self) -> str:
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}"
        return f"redis://{self.redis_host}:{self.redis_port}"

    @property
    def sqlalchemy_database_url(self) -> str:
        url = self.database_url
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+asyncpg://", 1)
        return url

    # Логи
    @property
    def log_file_debug(self) -> str:
        return f"{self.log_dir}/debug.log"

    @property
    def log_file_errors(self) -> str:
        return f"{self.log_dir}/errors.json"

    model_config = SettingsConfigDict(
        env_file=ENV_FILE_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
    )


# Mypy ругается на отсутствие аргументов, так как они берутся из .env
settings = Settings()  # type: ignore[call-arg]
