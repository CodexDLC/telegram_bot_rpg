# app/core/log_setup.py
import logging
import logging.config
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from colorlog import ColoredFormatter


def setup_logging(
    level: int | str = "INFO",  # общий уровень логирования
    to_file: bool = False,  # писать ли ещё и в файл
    log_path: str = "logs/app.log",  # путь к файлу лога
    max_bytes: int = 5 * 1024 * 1024,  # размер файла до ротации (5 МБ)
    backup_count: int = 3,  # сколько старых файлов хранить
) -> None:
    # 1) Базовый формат
    text_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

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
        secondary_log_colors={},
        style="%",
    )
    console_handler.setFormatter(console_fmt)

    handlers: list[logging.Handler] = [console_handler]
    # 3) Файловый хенд лер с ротацией

    if to_file:
        Path(log_path).parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            filename=log_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )

        file_handler.setLevel(level)
        file_handler.setFormatter(logging.Formatter(text_format, date_format))
        handlers.append(file_handler)

    logging.basicConfig(level=level, handlers=handlers)


    logging.getLogger("aiogram").setLevel("INFO")
    logging.getLogger("httpx").setLevel("WARNING")
    logging.getLogger("aiosqlite").setLevel("INFO")
