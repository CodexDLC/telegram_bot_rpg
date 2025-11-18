from aiogram import Bot, Dispatcher

# 1. ДОБАВИТЬ ЭТОТ ИМПОРТ
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.redis import RedisStorage
from loguru import logger as log
from redis.exceptions import ConnectionError as RedisConnectionError

from app.core.config import BOT_TOKEN, REDIS_URL
from app.core.redis_client import redis_client


async def build_app() -> tuple[Bot, Dispatcher]:
    """
    Асинхронно создает и конфигурирует экземпляры Bot и Dispatcher.

    Эта асинхронная фабрика инкапсулирует логику создания ключевых
    объектов aiogram и проверяет подключения к внешним сервисам (Redis).

    1.  Создает экземпляр `Bot`.
    2.  Подключается к Redis и создает `RedisStorage` для FSM.
    3.  Проверяет соединение с Redis.
    4.  Создает `Dispatcher` с настроенным хранилищем.

    Args:
        None

    Returns:
        Tuple[Bot, Dispatcher]: Кортеж с готовыми к работе экземплярами
                                `Bot` и `Dispatcher`.

    Raises:
        RuntimeError: Если не удалось подключиться к Redis.
    """
    log.info("Начало создания экземпляров Bot и Dispatcher...")

    if not BOT_TOKEN:
        log.critical("BOT_TOKEN не найден. Невозможно создать бота.")
        raise RuntimeError("BOT_TOKEN не найден.")

    # --- Создание бота ---
    # 2. ИЗМЕНИТЬ ЭТУ СТРОКУ
    # БЫЛО: bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))

    log.debug("Экземпляр Bot создан.")

    log.debug("Попытка подключения к Redis (проверка .ping())")
    try:
        # Вот здесь 'await' сработает, потому что мы внутри async def!
        if not await redis_client.ping():
            raise RedisConnectionError
        log.info("Соединение с Redis успешно установлено.")

    except RedisConnectionError as e:
        log.critical(f"Не удалось подключиться к Redis: {e}")
        raise RuntimeError(f"Критическая ошибка: не удалось подключиться к Redis по адресу {REDIS_URL}") from e

    # RedisStorage будет использоваться для машины состояний (FSM).
    storage = RedisStorage(redis=redis_client)
    log.debug("Хранилище состояний RedisStorage создано.")

    # --- Создание диспетчера ---
    dp = Dispatcher(storage=storage)
    log.debug("Экземпляр Dispatcher создан с RedisStorage.")

    log.info("Экземпляры Bot и Dispatcher успешно созданы и настроены.")
    return bot, dp
