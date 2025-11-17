# app/core/redis_client.py
from loguru import logger as log
from redis.asyncio import Redis
from app.core.config import REDIS_URL

# --- Настройки нашего пула соединений ---
# Это можно вынести в .env, если захочешь, но для старта можно и здесь
MAX_REDIS_CONNECTIONS = 50
REDIS_SOCKET_TIMEOUT = 5  # 5 секунд

# --- Создание Singleton'а ---
log.info(f"Создание 'ленивого' Redis-клиента (Singleton)...")
try:
    redis_client = Redis.from_url(
        REDIS_URL,
        decode_responses=True,

        # --- настройки ----------
        max_connections=MAX_REDIS_CONNECTIONS,
        socket_timeout=REDIS_SOCKET_TIMEOUT,
        socket_connect_timeout=REDIS_SOCKET_TIMEOUT
        # -------------------------
    )
    log.info(f"Redis Singleton создан (max_connections={MAX_REDIS_CONNECTIONS}).")

except Exception as e:
    log.critical(f"Критическая ошибка при *создании* Redis-клиента: {e}")
    # Если мы не можем даже создать объект, приложение не должно запускаться
    raise RuntimeError("Не удалось сконфигурировать Redis-клиент.")