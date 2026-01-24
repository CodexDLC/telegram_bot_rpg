from typing import Any

from arq.connections import ArqRedis, RedisSettings, create_pool

from backend.core.config import settings
from backend.database.redis.redis_service import RedisService
from common.core.client import get_redis_client


async def base_startup(ctx: dict) -> None:
    """
    Базовая инициализация для всех воркеров.
    Создает клиент Redis и RedisService.
    """
    # Используем нашу фабрику для создания клиента (с пулом и настройками)
    redis_client = await get_redis_client(settings)

    # Оборачиваем в сервис
    redis_service = RedisService(redis_client)

    ctx["redis_client_internal"] = redis_client
    ctx["redis_service"] = redis_service


async def base_shutdown(ctx: dict) -> None:
    """
    Базовая очистка ресурсов.
    """
    if "redis_client_internal" in ctx:
        # Закрываем соединение (или возвращаем в пул)
        await ctx["redis_client_internal"].close()


class BaseArqSettings:
    """
    Базовые настройки для всех ARQ воркеров в проекте.
    """

    redis_settings = RedisSettings(
        host=settings.redis_host,
        port=settings.redis_port,
        password=settings.redis_password,
        database=0,  # ARQ обычно использует 0, но можно вынести в конфиг
    )

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
