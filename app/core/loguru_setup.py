# app/core/loguru_setup.py

import logging
import sys
from types import FrameType

from loguru import logger


class InterceptHandler(logging.Handler):
    """
    Пользовательский класс-обработчик (Handler), который наследуется от
    стандартного logging.Handler.
    Его единственная задача — перехватывать все сообщения, отправленные
    в 'logging' (например, библиотеками aiogram, sqlalchemy),
    и "передавать" их 'loguru', чтобы они отображались в едином стиле.
    Минор обновление для теста бота хелпебра гитхаб
    """

    def emit(self, record: logging.LogRecord) -> None:
        """
        Этот метод вызывается автоматически для каждой записи лога.
        """
        try:
            # Пытаемся найти уровень loguru, соответствующий уровню logging
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            # Если не найден (например, кастомный уровень), используем
            # численный уровень
            level = record.levelno

        # Находим фрейм (кадр стека вызовов), где был сделан лог
        frame: FrameType | None = logging.currentframe()
        depth = 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        # Отправляем сообщение в loguru, "проваливаясь" (depth)
        # на нужную глубину стека, чтобы loguru показал
        # правильный файл и строку, где лог был вызван.
        logger.opt(depth=depth, exception=record.exc_info).log(
            level,
            record.getMessage(),
        )


def setup_loguru() -> None:
    """
    Настраивает Loguru, заменяя стандартную конфигурацию logging.
    """
    # 1. Сброс Loguru
    # Сначала удаляем хэндлер по умолчанию (который пишет в stderr),
    # чтобы мы могли настроить свои собственные.
    logger.remove()

    # 2. Настройка вывода в Консоль (stdout)
    # Это то, что ты будешь видеть при запуске бота.
    logger.add(
        sink=sys.stdout,  # "sink" (приемник) - это консоль
        level="DEBUG",  # В консоль будут падать только 'INFO' и важнее
        colorize=True,  # Включаем цвета (замена 'colorlog')
        format=(  # Задаем наш формат
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
    )

    # 3. Настройка вывода в Debug-файл (как ты и хотел)
    # Здесь будут храниться ВСЕ сообщения для детальной отладки.
    logger.add(
        sink="logs/debug.log",  # Файл для логов
        level="DEBUG",  # Уровень - ВСЕ, начиная с DEBUG
        rotation="10 MB",  # Ротация файла при достижении 10 MB
        compression="zip",  # Сжимать старые логи в .zip
        format="{time} | {level: <8} | {name}:{function}:{line} - {message}",
    )

    # 4. Настройка вывода Ошибок в JSON (твоя главная цель)
    # Отдельный файл только для критических сбоев в формате JSON.
    logger.add(
        sink="logs/errors.json",
        level="ERROR",  # Уровень - ТОЛЬКО ERROR и CRITICAL
        serialize=True,  # <-- МАГИЯ: Включает JSON-формат
        rotation="10 MB",  # Тоже с ротацией
        compression="zip",
    )

    # 5. Включение "Перехватчика"
    # Говорим стандартному 'logging', чтобы он отдал все свои
    # сообщения нашему InterceptHandler (Блок 1).
    logging.basicConfig(handlers=[InterceptHandler()], level=0)

    # 6. Настраиваем уровни сторонних библиотек (как в старом файле)
    # Мы говорим 'logging', чтобы он НЕ игнорировал сообщения INFO
    # от aiogram, а передавал их нашему 'InterceptHandler'.
    logging.getLogger("aiogram").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("aiosqlite").setLevel(logging.INFO)

    logger.info("Логгер Loguru успешно настроен и перехватил 'logging'.")
