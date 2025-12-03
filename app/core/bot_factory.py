from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.redis import RedisStorage
from loguru import logger as log
from redis.asyncio import Redis
from redis.exceptions import ConnectionError as RedisConnectionError

from app.core.config import BOT_TOKEN, REDIS_URL
from app.middlewares.db_session_middleware import DbSessionMiddleware
from database.session import async_session_factory


async def build_app(redis_client: Redis) -> tuple[Bot, Dispatcher]:
    """
    Создает и конфигурирует экземпляры Bot и Dispatcher.

    Фабрика инкапсулирует логику создания объектов aiogram, проверяет
    подключение к Redis и настраивает middlewares.

    Args:
        redis_client: Асинхронный клиент Redis.

    Returns:
        Кортеж с готовыми к работе экземплярами `Bot` и `Dispatcher`.

    Raises:
        RuntimeError: Если не удалось подключиться к Redis или отсутствует BOT_TOKEN.
    """
    log.info("AppBuild | status=started")

    if not BOT_TOKEN:
        log.critical("AppBuild | status=failed reason='BOT_TOKEN not found'")
        raise RuntimeError("BOT_TOKEN не найден.")

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    log.debug("AppBuild | component=Bot status=created")

    log.debug("RedisCheck | status=started")
    try:
        if not await redis_client.ping():
            raise RedisConnectionError("Redis ping failed")
        log.info("RedisCheck | status=success")

    except RedisConnectionError as e:
        log.critical(f"RedisCheck | status=failed error='{e}' url='{REDIS_URL}'", exc_info=True)
        raise RuntimeError(f"Критическая ошибка: не удалось подключиться к Redis по адресу {REDIS_URL}") from e

    storage = RedisStorage(redis=redis_client)
    log.debug("AppBuild | component=RedisStorage status=created")

    dp = Dispatcher(storage=storage)
    log.debug("AppBuild | component=Dispatcher status=created")

    dp.update.middleware(DbSessionMiddleware(session_pool=async_session_factory))
    log.info("AppBuild | component=DbSessionMiddleware status=registered")

    log.info("AppBuild | status=finished")
    return bot, dp
