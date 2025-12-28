import asyncio

from loguru import logger as log

from apps.bot.bot_container import BotContainer
from apps.bot.core_client.combat_rbc_client import CombatRBCClient
from apps.bot.handlers import router as main_router
from apps.bot.middlewares.container_middleware import ContainerMiddleware
from apps.bot.middlewares.throttling_middleware import ThrottlingMiddleware
from apps.common.core.bot_factory import build_app
from apps.common.core.container import AppContainer
from apps.common.core.loguru_setup import setup_loguru
from apps.game_core.core_container import CoreContainer

setup_loguru()


@log.catch
async def main() -> None:
    """
    Основная асинхронная функция для запуска приложения.
    """
    # 1. Инициализация контейнеров
    # Старый контейнер (для совместимости)
    app_container = AppContainer()

    # Новые контейнеры
    core_container = CoreContainer()
    bot_container = BotContainer(core_container)

    log.info("Запуск загрузки игрового мира в Redis...")
    try:
        loaded_count = await app_container.world_loader_service.init_world_cache()
        log.info(f"Игровой мир загружен успешно. Всего загружено нод: {loaded_count}")
    except RuntimeError as e:
        log.error(f"Критическая ошибка при загрузке игрового мира: {e}")
        return

    # Создаем бота (используем старый контейнер для настроек и редиса)
    bot, dp = await build_app(app_container)
    log.info("Экземпляры бота и диспетчера созданы.")

    # Подключаем middleware
    dp.update.middleware(ThrottlingMiddleware(redis=app_container.redis_client, rate_limit=1.0))

    # Передаем оба контейнера в middleware
    dp.update.middleware(ContainerMiddleware(app_container, bot_container))
    log.info("Middleware подключены.")

    # Подключаем все роутеры
    dp.include_router(main_router)
    log.info("Роутеры подключены.")

    log.info("Восстановление активных боевых сессий...")
    try:
        async with app_container.db_session_factory() as session:
            client = CombatRBCClient(session, app_container.account_manager, app_container.combat_manager)
            orchestrator = client._orchestrator
            await orchestrator.restore_active_battles()
    except Exception as e:  # noqa: BLE001
        log.error(f"Ошибка при восстановлении боев: {e}")

    log.info("Бот запускается...")
    try:
        await dp.start_polling(bot)
    finally:
        await app_container.shutdown()
        await core_container.shutdown()
        log.info("Соединения приложения закрыты.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        log.info("Бот остановлен.")
    except RuntimeError as e:
        log.critical(f"Критическая ошибка при запуске: {e}")
