# app/core/log_setup.py
import logging
import logging.config
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import List, Union

from colorlog import ColoredFormatter


def setup_logging(
    level: Union[int, str] = "INFO",
    to_file: bool = False,
    log_path: str = "logs/app.log",
    max_bytes: int = 5 * 1024 * 1024,  # 5 MB
    backup_count: int = 3,
) -> None:
    """
    Настраивает систему логирования для всего приложения.

    Эта функция конфигурирует:
    1.  **Консольный логгер:** Выводит цветные логи в stdout для удобства
        разработки.
    2.  **Файловый логгер (опционально):** Пишет логи в файл с ротацией,
        чтобы избежать переполнения диска.
    3.  Устанавливает уровни логирования для сторонних библиотек, чтобы
        уменьшить "шум" в логах.

    Args:
        level (Union[int, str], optional): Общий уровень логирования
            (e.g., "DEBUG", "INFO", logging.WARNING). Defaults to "INFO".
        to_file (bool, optional): Если True, логи будут дублироваться в файл.
            Defaults to False.
        log_path (str, optional): Путь к файлу лога. Defaults to "logs/app.log".
        max_bytes (int, optional): Максимальный размер файла лога в байтах
            до его ротации. Defaults to 5 * 1024 * 1024 (5 MB).
        backup_count (int, optional): Количество старых файлов логов,
            которые нужно хранить. Defaults to 3.

    Returns:
        None
    """
    # Получаем корневой логгер, чтобы добавить в него сообщения о настройке.
    # Это временная мера, пока basicConfig не будет вызван.
    log = logging.getLogger()
    log.setLevel("DEBUG")  # Временно ставим DEBUG, чтобы видеть все сообщения

    # --- 1. Настройка форматов ---
    text_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    log.debug("Форматы для логирования определены.")

    # --- 2. Настройка консольного обработчика с цветами ---
    console_handler = logging.StreamHandler(stream=sys.stdout)
    console_handler.setLevel(level)
    console_fmt = ColoredFormatter(
        "%(log_color)s%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt=date_format,
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "bold_red",
        },
    )
    console_handler.setFormatter(console_fmt)
    log.debug("Консольный обработчик (StreamHandler) настроен.")

    handlers: List[logging.Handler] = [console_handler]

    # --- 3. Настройка файлового обработчика с ротацией (если включено) ---
    if to_file:
        log.debug(f"Включено логирование в файл. Путь: {log_path}")
        # Создаем директорию для логов, если она не существует.
        log_dir = Path(log_path).parent
        log_dir.mkdir(parents=True, exist_ok=True)
        log.debug(f"Директория для логов '{log_dir}' проверена/создана.")

        # RotatingFileHandler автоматически управляет размером и количеством файлов.
        file_handler = RotatingFileHandler(
            filename=log_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(logging.Formatter(text_format, date_format))
        handlers.append(file_handler)
        log.debug("Файловый обработчик (RotatingFileHandler) настроен.")
    else:
        log.debug("Логирование в файл отключено.")

    # --- 4. Применение конфигурации ---
    # logging.basicConfig должен вызываться один раз. Он настраивает корневой логгер.
    # force=True (в Python 3.8+) позволяет перенастроить логгер, если он уже был настроен.
    logging.basicConfig(level=level, handlers=handlers, force=True)
    log.info(f"Система логирования настроена. Общий уровень: {level}.")

    # --- 5. Настройка уровней для сторонних библиотек ---
    # Уменьшаем "шум" от библиотек, логи которых не так важны в обычном режиме.
    logging.getLogger("aiogram").setLevel("INFO")
    logging.getLogger("httpx").setLevel("WARNING")
    logging.getLogger("aiosqlite").setLevel("INFO")
    logging.getLogger("sqlalchemy").setLevel("WARNING")
    log.debug("Уровни логирования для сторонних библиотек (aiogram, httpx, aiosqlite, sqlalchemy) установлены.")

    log.info("Настройка логирования завершена.")
