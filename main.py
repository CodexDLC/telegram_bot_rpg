import asyncio

from loguru import logger as log

from apps.bot.handlers import router as main_router
from apps.bot.middlewares.container_middleware import ContainerMiddleware
from apps.common.core.bot_factory import build_app
from apps.common.core.config import BOT_TOKEN, REDIS_URL  # Используются для проверки
from apps.common.core.container import AppContainer
from apps.common.core.loguru_setup import setup_loguru

# Импорты должны быть корректными. Я предполагаю, что вы импортируете AppContainer,
# который мы обновили, и все остальные зависимости


setup_loguru()


@log.catch
async def main() -> None:
    """
    Основная асинхронная функция для запуска приложения.
    """

    if BOT_TOKEN is None:
        log.critical("Токен бота не найден. Убедитесь, что он задан в .env файле.")
        return

    if REDIS_URL is None:
        log.critical("URL Redis не найден. Убедитесь, что он задан в .env файле.")
        return

    # 1. Создаем контейнер, где теперь настроены Redis и SQLAlchemy
    container = AppContainer()

    # Загрузка игрового мира в Redis
    log.info("Запуск загрузки игрового мира в Redis...")

    # 🔥 ИСПРАВЛЕНИЕ 1: Имя инъекции изменено с game_world_service на world_loader_service
    # 🔥 ИСПРАВЛЕНИЕ 2: Имя метода изменено на init_world_cache()
    # 🔥 ИСПРАВЛЕНИЕ 3: Получаем и логируем количество загруженных нод (int)
    try:
        loaded_count = await container.world_loader_service.init_world_cache()
        log.info(f"Игровой мир загружен успешно. Всего загружено нод: {loaded_count}")
    except RuntimeError as e:
        log.error(f"Критическая ошибка при загрузке игрового мира: {e}")
        # Если мир не загрузился, возможно, стоит остановить запуск бота
        return

    # Создаем экземпляры бота и диспетчера с помощью фабрики.
    bot, dp = await build_app(container.redis_client)
    log.info("Экземпляры бота и диспетчера созданы.")

    # Подключаем middleware
    dp.update.middleware(ContainerMiddleware(container))
    log.info("Middleware контейнера подключен.")

    # Подключаем все роутеры
    dp.include_router(main_router)
    log.info("Роутеры подключены.")

    log.info("Бот запускается...")
    try:
        # Запускаем бота в режиме long-polling.
        await dp.start_polling(bot)
    finally:
        # shutdown контейнера теперь включает закрытие Redis и SQLAlchemy
        await container.shutdown()
        log.info("Соединения приложения закрыты.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        log.info("Бот остановлен.")
    except RuntimeError as e:
        log.critical(f"Критическая ошибка при запуске: {e}")
