import logging
import sys
from types import FrameType

from loguru import logger

from .settings import settings  # <-- Импортируем наш объект настроек


class InterceptHandler(logging.Handler):
    """
    Перехватывает стандартные сообщения `logging` и направляет их в `loguru`.
    """

    def emit(self, record: logging.LogRecord) -> None:
        """Перенаправляет запись лога в loguru."""
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame: FrameType | None = logging.currentframe()
        depth = 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level,
            record.getMessage(),
        )


def setup_loguru() -> None:
    """
    Настраивает loguru для проекта, используя переменные из settings.
    """
    logger.remove()

    # Консольный вывод
    logger.add(
        sink=sys.stdout,
        level=settings.log_level_console.upper(),  # <-- Используем настройки
        colorize=True,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
    )

    # Файл для всех логов уровня DEBUG и выше
    logger.add(
        sink=settings.log_file_debug,  # <-- Используем настройки
        level=settings.log_level_file.upper(),  # <-- Используем настройки
        rotation=settings.log_rotation,  # <-- Используем настройки
        compression="zip",
        format="{time} | {level: <8} | {name}:{function}:{line} - {message}",
    )

    # JSON-файл для логов уровня ERROR и выше
    logger.add(
        sink=settings.log_file_errors,  # <-- Используем настройки
        level="ERROR",
        serialize=True,
        rotation=settings.log_rotation,  # <-- Используем настройки
        compression="zip",
    )

    # Перехват стандартного logging
    logging.basicConfig(handlers=[InterceptHandler()], level=0)

    # Настройка уровней логов для сторонних библиотек
    logging.getLogger("aiogram").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("aiosqlite").setLevel(logging.INFO)

    logger.info("LoggerSetup | status=success message='Loguru configured and intercepted logging'")
