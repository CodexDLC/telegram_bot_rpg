import json
from typing import Any

from loguru import logger as log
from redis.asyncio import Redis


class ContextRedisManager:
    """
    Менеджер для работы с временными контекстами (снапшотами) в Redis.
    Используется ContextAssembler для сохранения результатов сборки.
    """

    def __init__(self, redis: Redis):
        self.redis = redis

    async def save_context_batch(self, data_map: dict[int | str, tuple[str, dict[str, Any]]], ttl: int = 90) -> None:
        """
        Массовое сохранение контекстов в Redis.

        Args:
            data_map: Словарь {entity_id: (redis_key, context_data_dict)}.
            ttl: Время жизни ключа в секундах.
        """
        if not data_map:
            return

        async with self.redis.pipeline() as pipe:
            for _, (key, data) in data_map.items():
                try:
                    json_data = json.dumps(data)
                    pipe.set(key, json_data, ex=ttl)
                except (TypeError, ValueError) as e:
                    log.error(f"ContextRedisManager | serialization failed key={key} error={e}")

            await pipe.execute()

        log.debug(f"ContextRedisManager | saved batch count={len(data_map)}")

    async def get_context(self, key: str) -> dict[str, Any] | None:
        """Получение контекста по ключу."""
        data = await self.redis.get(key)
        if not data:
            return None
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            log.error(f"ContextRedisManager | decode failed key={key}")
            return None
