from loguru import logger as log
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import REDIS_URL

# TODO: Вынести настройки пула соединений в .env файл.
MAX_REDIS_CONNECTIONS = 50
REDIS_SOCKET_TIMEOUT = 5  # 5 секунд

log.info("RedisClient | status=initializing")
try:
    redis_client = Redis.from_url(
        REDIS_URL,
        decode_responses=True,
        max_connections=MAX_REDIS_CONNECTIONS,
        socket_timeout=REDIS_SOCKET_TIMEOUT,
        socket_connect_timeout=REDIS_SOCKET_TIMEOUT,
    )
    log.info(f"RedisClient | status=created max_connections={MAX_REDIS_CONNECTIONS}")

except RedisError as e:
    log.critical(f"RedisClient | status=failed_to_create error='{e}'", exc_info=True)
    raise RuntimeError("Не удалось сконфигурировать Redis-клиент.") from e
