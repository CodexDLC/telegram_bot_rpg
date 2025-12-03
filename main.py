import asyncio

from loguru import logger as log

from app.core.bot_factory import build_app
from app.core.config import BOT_TOKEN, REDIS_URL
from app.core.container import AppContainer
from app.core.loguru_setup import setup_loguru
from app.handlers import router as main_router
from app.middlewares.container_middleware import ContainerMiddleware
from database.session import create_db_tables as create_tables

setup_loguru()


@log.catch
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

    log.info("Инициализация базы данных...")
    await create_tables()
    log.info("Инициализация базы данных завершена.")

    if BOT_TOKEN is None:
        log.critical("Токен бота не найден. Убедитесь, что он задан в .env файле.")
        return

    if REDIS_URL is None:
        log.critical("URL Redis не найден. Убедитесь, что он задан в .env файле.")
        return

    container = AppContainer()

    # Загрузка игрового мира в Redis
    log.info("Загрузка игрового мира в Redis...")
    await container.game_world_service.initialize_world_locations()
    log.info("Игровой мир загружен.")

    # Создаем экземпляры бота и диспетчера с помощью фабрики.
    bot, dp = await build_app(container.redis_client)
    log.info("Экземпляры бота и диспетчера созданы.")

    # Подключаем middleware
    dp.update.middleware(ContainerMiddleware(container))
    log.info("Middleware контейнера подключен.")

    # Подключаем все роутеры, собранные в app/handlers/__init__.py
    dp.include_router(main_router)
    log.info("Роутеры подключены.")

    log.info("Бот запускается...")
    try:
        # Запускаем бота в режиме long-polling.
        await dp.start_polling(bot)
    finally:
        await container.close()
        log.info("Соединение с Redis закрыто.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        log.info("Бот остановлен.")
    except RuntimeError as e:
        log.critical(f"Критическая ошибка при запуске: {e}")
