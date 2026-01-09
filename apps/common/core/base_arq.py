from typing import Any

from arq.connections import ArqRedis, RedisSettings, create_pool
from redis.asyncio import Redis

from apps.common.services.redis.redis_service import RedisService

# TODO: Load from config (env vars)
REDIS_HOST = "redis"
REDIS_PORT = 6379


async def base_startup(ctx: dict) -> None:
    """
    Базовая инициализация для всех воркеров.
    Создает клиент Redis и RedisService.
    """
    # Создаем клиент Redis (используем те же настройки, что и ARQ)
    # Важно: decode_responses=True для удобства работы с JSON/строками
    redis_client = Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    redis_service = RedisService(redis_client)

    ctx["redis_client_internal"] = redis_client
    ctx["redis_service"] = redis_service


async def base_shutdown(ctx: dict) -> None:
    """
    Базовая очистка ресурсов.
    """
    if "redis_client_internal" in ctx:
        await ctx["redis_client_internal"].aclose()


class BaseArqSettings:
    """
    Базовые настройки для всех ARQ воркеров в проекте.
    """

    redis_settings = RedisSettings(host=REDIS_HOST, port=REDIS_PORT)
    max_jobs = 20
    job_timeout = 60
    keep_result = 5

    on_startup = base_startup
    on_shutdown = base_shutdown


class ArqService:
    """
    Обертка над клиентом ARQ.
    Позволяет создавать пул один раз и переиспользовать его.
    """

    def __init__(self):
        self.pool: ArqRedis | None = None

    async def init(self):
        """Инициализация пула (вызывать при старте приложения)."""
        if not self.pool:
            self.pool = await create_pool(BaseArqSettings.redis_settings)

    async def close(self):
        """Закрытие пула (вызывать при остановке приложения)."""
        if self.pool:
            await self.pool.close()

    async def enqueue_job(self, function: str, *args: Any, **kwargs: Any) -> Any | None:
        """
        Отправка задачи в очередь.
        """
        if not self.pool:
            # Ленивая инициализация (на случай, если init не вызвали)
            await self.init()

        if self.pool:
            return await self.pool.enqueue_job(function, *args, **kwargs)
        return None


async def get_arq_pool() -> ArqRedis:
    """
    Хелпер для получения сырого пула (если нужно).
    """
    return await create_pool(BaseArqSettings.redis_settings)
