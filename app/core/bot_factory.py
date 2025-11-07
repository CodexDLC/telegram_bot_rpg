# app/core/bot_factory.py
import logging
from typing import Tuple

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

from app.core.config import REDIS_URL

log = logging.getLogger(__name__)


def build_app(token: str) -> Tuple[Bot, Dispatcher]:
    """
    Создает и конфигурирует экземпляры Bot и Dispatcher.

    Эта функция-фабрика инкапсулирует логику создания ключевых объектов
    aiogram:
    1.  Создает экземпляр `Bot`.
    2.  Подключается к Redis и создает `RedisStorage` для хранения состояний FSM.
    3.  Создает экземпляр `Dispatcher` с настроенным хранилищем.

    Использование фабрики позволяет легко переключать компоненты (например,
    хранилище) и упрощает инициализацию приложения в `main.py`.

    Args:
        token (str): Токен Telegram-бота.

    Returns:
        Tuple[Bot, Dispatcher]: Кортеж с готовыми к работе экземплярами
        `Bot` и `Dispatcher`.
    """
    bot = Bot(token)
    log.info("Экземпляр Bot создан.")

    # Создаем клиент для подключения к Redis.
    redis_client = Redis.from_url(REDIS_URL)
    log.info(f"Подключение к Redis по адресу: {REDIS_URL}")

    # RedisStorage будет использоваться для машины состояний (FSM).
    # Это позволяет сохранять состояния пользователей даже после перезапуска бота.
    storage = RedisStorage(redis=redis_client)

    dp = Dispatcher(storage=storage)
    log.info("Экземпляр Dispatcher создан с RedisStorage.")

    return bot, dp
