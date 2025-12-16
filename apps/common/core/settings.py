from pydantic_settings import BaseSettings, SettingsConfigDict


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
    database_url: str = "sqlite+aiosqlite:///./game.db"

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

    @property
    def system_char_id(self) -> int:
        return self.system_user_id

    # --- Свойства и Валидаторы ---

    @property
    def get_admin_ids(self) -> list[int]:
        """Парсит строку '123,456' в список чисел."""
        if not self.admin_ids:
            return []
        try:
            return [int(x.strip()) for x in self.admin_ids.split(",") if x.strip()]
        except ValueError:
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
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# Mypy ругается на отсутствие аргументов, так как они берутся из .env
settings = Settings()  # type: ignore[call-arg]
