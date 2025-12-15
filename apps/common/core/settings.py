from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- БЛОК 1: Переменные (имена как в .env, регистр не важен) ---
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str | None = None

    redis_max_connections: int = 50
    redis_timeout: int = 5

    # --- НОВЫЙ БЛОК: Настройки Логирования ---
    log_level_console: str = "DEBUG"
    log_level_file: str = "DEBUG"
    log_rotation: str = "10 MB"
    log_dir: str = "logs"  # Папка для логов

    @property
    def log_file_debug(self) -> str:
        """Путь к основному файлу логов."""
        return f"{self.log_dir}/debug.log"

    @property
    def log_file_errors(self) -> str:
        """Путь к JSON-файлу с ошибками."""
        return f"{self.log_dir}/errors.json"

    # -----------------------------------------

    # --- БЛОК 2: Логика сборки URL (замена твоего старого конфига) ---
    @property
    def redis_url(self) -> str:
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}"
        return f"redis://{self.redis_host}:{self.redis_port}"

    # --- БЛОК 3: Настройки самого Pydantic ---
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# Создаем объект, который будем импортировать
settings = Settings()
