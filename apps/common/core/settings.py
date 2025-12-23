from pathlib import Path

from loguru import logger as log
from pydantic_settings import BaseSettings, SettingsConfigDict

# Определяем корень проекта
# settings.py -> core -> common -> apps -> ROOT
ROOT_DIR = Path(__file__).parent.parent.parent.parent
ENV_FILE_PATH = ROOT_DIR / ".env"


class Settings(BaseSettings):
    # --- БЛОК 0: Токены (Критичные данные) ---
    bot_token: str
    gemini_token: str

    # --- БЛОК 1: Redis ---
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str | None = None
    redis_max_connections: int = 50
    redis_timeout: int = 5

    # --- БЛОК 2: База Данных ---
    database_url: str  # Основная база
    test_database_url: str | None = None  # Тестовая база (опционально)

    # Флаг для SSL подключения к БД (True для Neon/Cloud, False для локального Docker)
    db_ssl_require: bool = True

    # --- БЛОК 3: Логирование ---
    log_level_console: str = "DEBUG"
    log_level_file: str = "DEBUG"
    log_rotation: str = "10 MB"
    log_dir: str = "logs"

    # --- БЛОК 4: Игровые настройки и Каналы ---
    bug_report_channel_id: int | None = None
    admin_ids: str = ""
    system_user_id: int = 2_000_000_000
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

    def _fix_postgres_url(self, url: str) -> str:
        """Принудительно ставит драйвер asyncpg для Postgres."""
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+asyncpg://", 1)
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    @property
    def sqlalchemy_database_url(self) -> str:
        """URL для основной базы."""
        return self._fix_postgres_url(self.database_url)

    @property
    def sqlalchemy_test_database_url(self) -> str:
        """URL для тестовой базы. Если не задан, используется основная."""
        url = self.test_database_url or self.database_url
        return self._fix_postgres_url(url)

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
