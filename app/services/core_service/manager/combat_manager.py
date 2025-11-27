# app/services/core_service/manager/combat_manager.py
from typing import Any

from app.core.redis_client import redis_client
from app.services.core_service.redis_key import RedisKeys as Rk
from app.services.core_service.redis_service import redis_service


class CombatManager:
    """
    CRUD-менеджер для боевых сессий.
    Изолирует работу с ключами Redis и сырыми данными.
    """

    # --- META (Hash) ---
    async def create_session_meta(self, session_id: str, data: dict) -> None:
        """Создает мета-данные боя."""
        key = Rk.get_combat_meta_key(session_id)
        await redis_service.set_hash_fields(key, data)

    async def get_session_meta(self, session_id: str) -> dict[str, Any] | None:
        key = Rk.get_combat_meta_key(session_id)
        return await redis_service.get_all_hash(key)

    # --- ACTOR (JSON String) ---
    async def save_actor_json(self, session_id: str, char_id: int, json_data: str) -> None:
        """Сохраняет JSON-слепок бойца."""
        key = Rk.get_combat_actor_key(session_id, char_id)
        await redis_client.set(key, json_data)

    async def get_actor_json(self, session_id: str, char_id: int) -> str | None:
        """Получает JSON-слепок бойца."""
        key = Rk.get_combat_actor_key(session_id, char_id)
        return await redis_client.get(key)

    # --- PENDING MOVES (JSON String) ---
    async def set_pending_move(self, session_id: str, char_id: int, move_data: str) -> None:
        key = Rk.get_combat_pending_move_key(session_id, char_id)
        await redis_client.set(key, move_data)

    async def get_pending_move(self, session_id: str, char_id: int) -> str | None:
        key = Rk.get_combat_pending_move_key(session_id, char_id)
        return await redis_client.get(key)

    async def delete_pending_moves(self, session_id: str, *char_ids: int) -> None:
        keys = [Rk.get_combat_pending_move_key(session_id, cid) for cid in char_ids]
        if keys:
            await redis_client.delete(*keys)

    # --- LOGS (List) ---
    async def push_combat_log(self, session_id: str, log_entry_json: str) -> None:
        key = Rk.get_combat_log_key(session_id)
        await redis_client.rpush(key, log_entry_json)


# Singleton
combat_manager = CombatManager()
