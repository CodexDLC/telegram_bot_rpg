from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- БЛОК 1: Переменные (имена как в .env, регистр не важен) ---
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str | None = None  # Может быть пустым (None)

    # Настройки пула (ради которых мы всё затеяли)
    redis_max_connections: int = 50
    redis_timeout: int = 5

    # --- БЛОК 2: Логика сборки URL (замена твоего старого конфига) ---
    @property
    def redis_url(self) -> str:
        if self.redis_password:
            # Если пароль есть -> redis://:пароль@хост:порт
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}"

        # Если пароля нет -> redis://хост:порт
        return f"redis://{self.redis_host}:{self.redis_port}"

    # --- БЛОК 3: Настройки самого Pydantic ---
    class Config:
        env_file = ".env"  # Имя файла
        env_file_encoding = "utf-8"  # Кодировка
        extra = "ignore"  # ВАЖНО: Игнорировать чужие переменные (токены бота и т.д.)


# Создаем объект, который будем импортировать
settings = Settings()
