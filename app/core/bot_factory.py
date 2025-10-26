# app/core/bot_factory.py
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

from app.core.config import REDIS_URL

log = logging.getLogger(__name__)

def build_app(token: str ) -> tuple[Bot, Dispatcher]:
    bot = Bot(token)
    log.info("Бот создан")
    redis_client = Redis.from_url(REDIS_URL)
    log.info("Подключение к Redis установлено")
    storage = RedisStorage(redis=redis_client)

    dp = Dispatcher(storage=storage)
    log.info("Диспетчер создан")

    return bot, dp


