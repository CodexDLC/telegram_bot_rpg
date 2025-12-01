# app/services/core_service/manager/arena_manager.py
import json

from app.services.core_service.redis_key import RedisKeys as Rk
from app.services.core_service.redis_service import redis_service


class ArenaManager:
    """
    CRUD-Менеджер для работы с очередями Арены в Redis.
    """

    # --- Работа с заявкой (Request Meta) ---

    async def create_request(self, char_id: int, meta: dict, ttl: int = 300) -> None:
        """Создает запись о заявке с TTL."""
        key = Rk.get_arena_request_key(char_id)
        # Используем новый метод сервиса
        await redis_service.set_value(key, json.dumps(meta), ttl=ttl)

    async def get_request(self, char_id: int) -> dict | None:
        key = Rk.get_arena_request_key(char_id)
        raw = await redis_service.get_value(key)
        if raw:
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return None
        return None

    async def delete_request(self, char_id: int) -> None:
        key = Rk.get_arena_request_key(char_id)
        await redis_service.delete_key(key)

    # --- Работа с Очередью (ZSET) ---

    async def add_to_queue(self, mode: str, char_id: int, score: float) -> None:
        """Добавляет игрока в ZSET очереди."""
        key = Rk.get_arena_queue_key(mode)
        # Используем метод, который мы добавили в RedisService
        await redis_service.add_to_zset(key, {str(char_id): score})

    async def remove_from_queue(self, mode: str, char_id: int) -> bool:
        """Убирает игрока из очереди."""
        key = Rk.get_arena_queue_key(mode)
        return await redis_service.remove_from_zset(key, str(char_id))

    async def get_candidates(self, mode: str, min_score: float, max_score: float) -> list[str]:
        """Ищет игроков в диапазоне GS."""
        key = Rk.get_arena_queue_key(mode)
        return await redis_service.get_zset_range_by_score(key, min_score, max_score)

    async def get_score(self, mode: str, char_id: int) -> float | None:
        key = Rk.get_arena_queue_key(mode)
        return await redis_service.get_zset_score(key, str(char_id))


arena_manager = ArenaManager()
