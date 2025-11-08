import asyncio
import logging

from app.core.bot_factory import build_app
from app.core.config import BOT_TOKEN
from app.core.log_setup import setup_logging
from app.handlers import router as main_router
from database.session import create_db_tables as create_tables

# Настраиваем логирование при старте приложения.
# Уровень "DEBUG" и вывод в файл можно будет изменить для продакшена.
setup_logging(level="DEBUG", to_file=True)


async def main() -> None:
    """
    Основная асинхронная функция для запуска приложения.

    Выполняет следующие шаги:
    1. Инициализирует таблицы в базе данных.
    2. Создает экземпляры бота и диспетчера.
    3. Подключает основной роутер.
    4. Запускает long-polling для получения обновлений от Telegram.

    Returns:
        None
    """
    log = logging.getLogger(__name__)

    log.info("Инициализация базы данных...")
    await create_tables()
    log.info("Инициализация базы данных завершена.")

    if BOT_TOKEN is None:
        log.critical("Токен бота не найден. Убедитесь, что он задан в .env файле.")
        return

    # Создаем экземпляры бота и диспетчера с помощью фабрики.
    bot, dp = await build_app()
    log.info("Экземпляры бота и диспетчера созданы.")

    # Подключаем все роутеры, собранные в app/handlers/__init__.py
    dp.include_router(main_router)
    log.info("Роутеры подключены.")

    log.info("Бот запускается...")
    # Запускаем бота в режиме long-polling.
    await dp.start_polling(bot)


if __name__ == "__main__":
    # Используем asyncio.run() для запуска асинхронной функции main.
    # Это стандартный способ запуска асинхронных приложений в Python.
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.getLogger(__name__).info("Бот остановлен.")
    except Exception as e:
        logging.getLogger(__name__).critical(f"Критическая ошибка при запуске: {e}", exc_info=True)
