from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.redis import RedisStorage
from loguru import logger as log
from redis.asyncio import Redis
from redis.exceptions import ConnectionError as RedisConnectionError

# TODO: Import Settings from shared/core/settings when available
# from shared.core.settings import Settings


async def build_bot(token: str, redis_client: Redis) -> tuple[Bot, Dispatcher]:
    """
    Создает и конфигурирует экземпляры Bot и Dispatcher.
    БЕЗ доступа к БД (DbSessionMiddleware удален).
    """
    log.info("BotFactory | status=started")

    if not token:
        log.critical("BotFactory | status=failed reason='BOT_TOKEN not found'")
        raise RuntimeError("BOT_TOKEN не найден.")

    bot = Bot(token=token, default=DefaultBotProperties(parse_mode="HTML"))
    log.debug("BotFactory | component=Bot status=created")

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
    log.debug("BotFactory | component=RedisStorage status=created")

    # Контейнер больше не передается в Dispatcher глобально,
    # зависимости должны внедряться через Middleware или ContextVar при необходимости,
    # либо использоваться явно в хендлерах (хотя лучше через DI).
    dp = Dispatcher(storage=storage)
    log.debug("BotFactory | component=Dispatcher status=created")

    log.info("BotFactory | status=finished")
    return bot, dp
