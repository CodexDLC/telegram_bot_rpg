from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.redis import RedisStorage
from loguru import logger as log
from redis.exceptions import ConnectionError as RedisConnectionError

from apps.bot.middlewares.db_session_middleware import DbSessionMiddleware
from apps.common.core.container import AppContainer


async def build_app(container: AppContainer) -> tuple[Bot, Dispatcher]:
    """
    Создает и конфигурирует экземпляры Bot и Dispatcher, используя DI-контейнер.

    Args:
        container: Экземпляр AppContainer с зависимостями.

    Returns:
        Кортеж с готовыми к работе экземплярами `Bot` и `Dispatcher`.

    Raises:
        RuntimeError: Если не удалось подключиться к Redis или отсутствует BOT_TOKEN.
    """
    log.info("AppBuild | status=started")

    bot_token = container.settings.bot_token
    if not bot_token:
        log.critical("AppBuild | status=failed reason='BOT_TOKEN not found'")
        raise RuntimeError("BOT_TOKEN не найден.")

    bot = Bot(token=bot_token, default=DefaultBotProperties(parse_mode="HTML"))
    log.debug("AppBuild | component=Bot status=created")

    redis_client = container.redis_client
    log.debug("RedisCheck | status=started")
    try:
        pong = await redis_client.ping()
        if not pong:
            raise RedisConnectionError("Redis ping failed")
        log.info("RedisCheck | status=success")
    except RedisConnectionError as e:
        log.critical(f"RedisCheck | status=failed error='{e}'", exc_info=True)
        raise RuntimeError("Критическая ошибка: не удалось подключиться к Redis.") from e

    storage = RedisStorage(redis=redis_client)
    log.debug("AppBuild | component=RedisStorage status=created")

    # Передаем контейнер в Dispatcher, чтобы он был доступен в хэндлерах
    dp = Dispatcher(storage=storage, container=container)
    log.debug("AppBuild | component=Dispatcher status=created")

    # Берем фабрику сессий из контейнера
    session_pool = container.db_session_factory
    dp.update.middleware(DbSessionMiddleware(session_pool=session_pool))
    log.info("AppBuild | component=DbSessionMiddleware status=registered")

    log.info("AppBuild | status=finished")
    return bot, dp
