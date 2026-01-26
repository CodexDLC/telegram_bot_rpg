# backend/database/redis/manager/scenario_manager.py
import json
from typing import Any

from backend.database.redis.redis_key import RedisKeys
from backend.database.redis.redis_service import RedisService


class ScenarioManager:
    """
    Низкоуровневый менеджер для работы с данными сценария в Redis.
    Отвечает за:
    1. Хранение сессии (scenario:session:{char_id}).
    2. Кэширование статических данных квеста (scenario:static:{quest_key}).
    """

    STATIC_TTL = 3600  # Время жизни кэша квеста (1 час)

    def __init__(self, redis_service: RedisService):
        self.redis = redis_service

    # --- Session Management ---

    async def get_session_context(self, char_id: int) -> dict[str, Any]:
        """Прямое получение из Redis."""
        key = RedisKeys.get_scenario_session_key(char_id)
        raw_data = await self.redis.get_all_hash(key)
        if not raw_data:
            return {}

        context: dict[str, Any] = {}
        for k, v in raw_data.items():
            if v == "null":
                context[k] = None
                continue

            try:
                context[k] = json.loads(v)
            except (json.JSONDecodeError, TypeError):
                if v.isdigit():
                    context[k] = int(v)
                else:
                    try:
                        context[k] = float(v)
                    except ValueError:
                        context[k] = v
        return context

    async def save_session_context(self, char_id: int, context: dict[str, Any], ttl: int = 86400):
        """Сохранение в Redis."""
        key = RedisKeys.get_scenario_session_key(char_id)
        if not context:
            return

        processed_context = {}
        for k, v in context.items():
            if v is None:
                processed_context[k] = "null"
            elif isinstance(v, (dict, list, bool)):
                processed_context[k] = json.dumps(v, ensure_ascii=False)
            else:
                processed_context[k] = v

        await self.redis.set_hash_fields(key, processed_context)
        await self.redis.expire(key, ttl)

    async def clear_session(self, char_id: int):
        """Удаляет сессию из Redis."""
        key = RedisKeys.get_scenario_session_key(char_id)
        await self.redis.delete_key(key)

    # --- Static Cache Management ---

    async def cache_quest_static_data(self, quest_key: str, master_data: dict, nodes_data: list[dict]) -> None:
        """
        Сохраняет статические данные квеста в Redis.
        """
        key = f"scenario:static:{quest_key}"
        data = {
            "master": json.dumps(master_data, ensure_ascii=False, default=str),
        }

        for node in nodes_data:
            n_id = node.get("node_key") or node.get("id")
            if n_id:
                data[f"node:{n_id}"] = json.dumps(node, ensure_ascii=False, default=str)

        if data:
            await self.redis.set_hash_fields(key, data)
            await self.redis.expire(key, self.STATIC_TTL)

    async def get_cached_node(self, quest_key: str, node_key: str) -> dict[str, Any] | None:
        """Получает ноду из кэша."""
        key = f"scenario:static:{quest_key}"
        cached_json = await self.redis.get_hash_field(key, f"node:{node_key}")
        if cached_json:
            try:
                return json.loads(cached_json)
            except json.JSONDecodeError:
                pass
        return None

    async def get_cached_master(self, quest_key: str) -> dict[str, Any] | None:
        """Получает мастер-данные из кэша."""
        key = f"scenario:static:{quest_key}"
        cached_json = await self.redis.get_hash_field(key, "master")
        if cached_json:
            try:
                return json.loads(cached_json)
            except json.JSONDecodeError:
                pass
        return None

    async def get_all_cached_data(self, quest_key: str) -> dict[str, str] | None:
        """Получает весь хэш квеста (для поиска по тегам)."""
        key = f"scenario:static:{quest_key}"
        return await self.redis.get_all_hash(key)

    async def has_static_cache(self, quest_key: str) -> bool:
        """Проверяет наличие кэша."""
        key = f"scenario:static:{quest_key}"
        return await self.redis.key_exists(key)
