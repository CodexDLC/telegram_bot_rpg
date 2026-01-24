from typing import Annotated

from fastapi import Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.database.redis.container import RedisContainer
from common.core.client import get_redis_client
from common.core.config import CommonSettings

# --- Base Dependencies ---

# Database Session
DbSessionDep = Annotated[AsyncSession, Depends(get_db)]


# Settings (Singleton-like via lru_cache or just instance)
def get_settings() -> CommonSettings:
    from backend.core.config import settings

    return settings


SettingsDep = Annotated[CommonSettings, Depends(get_settings)]


# Redis Client
async def get_redis(settings: SettingsDep) -> Redis:
    return await get_redis_client(settings)


RedisDep = Annotated[Redis, Depends(get_redis)]


# Redis Container (Unified Access)
async def get_redis_container(redis: RedisDep) -> RedisContainer:
    """
    Creates a RedisContainer with all managers initialized.
    """
    return RedisContainer(redis)


RedisContainerDep = Annotated[RedisContainer, Depends(get_redis_container)]
