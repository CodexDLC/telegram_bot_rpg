import asyncio
import sys
from pathlib import Path

# Добавляем корень проекта в sys.path
sys.path.append(str(Path(__file__).parent.parent))

from apps.common.core.settings import settings
from loguru import logger as log
from redis.asyncio import Redis

from backend.database.redis import RedisService


async def main():
    quest_key = "awakening_rift"

    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    redis_service = RedisService(redis)

    key = f"scenario:static:{quest_key}"

    if await redis.exists(key):
        await redis_service.delete_key(key)
        log.info(f"Cache cleared for: {key}")
    else:
        log.info(f"Cache not found for: {key}")

    await redis.aclose()


if __name__ == "__main__":
    asyncio.run(main())
