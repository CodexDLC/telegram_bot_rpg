# app/services/core_service/manager/combat_manager.py
from typing import Any

from app.services.core_service.redis_key import RedisKeys as Rk
from app.services.core_service.redis_service import redis_service


class CombatManager:
    """
    CRUD-менеджер для управления данными боевых сессий в Redis.
    Использует RedisService для всех операций.
    """

    # --- META (Hash) ---
    async def create_session_meta(self, session_id: str, data: dict) -> None:
        key = Rk.get_combat_meta_key(session_id)
        await redis_service.set_hash_fields(key, data)

    async def get_session_meta(self, session_id: str) -> dict[str, Any] | None:
        key = Rk.get_combat_meta_key(session_id)
        return await redis_service.get_all_hash(key)

    # --- PARTICIPANTS (Set) ---
    async def add_participant_id(self, session_id: str, char_id: int) -> None:
        key = Rk.get_combat_participants_key(session_id)
        await redis_service.add_to_set(key, str(char_id))

    async def get_session_participants(self, session_id: str) -> set[str]:
        key = Rk.get_combat_participants_key(session_id)
        return await redis_service.get_to_set(key)

    # --- ACTOR (JSON String) ---
    async def save_actor_json(self, session_id: str, char_id: int, json_data: str) -> None:
        key = Rk.get_combat_actor_key(session_id, char_id)
        # БЫЛО: await redis_client.set(key, json_data)
        # СТАЛО:
        await redis_service.set_value(key, json_data)

    async def get_actor_json(self, session_id: str, char_id: int) -> str | None:
        key = Rk.get_combat_actor_key(session_id, char_id)
        return await redis_service.get_value(key)

    # --- MOVES (Pending) ---
    async def set_pending_move(self, session_id: str, actor_id: int, target_id: int, move_data: str) -> None:
        key = Rk.get_combat_pending_move_key(session_id, actor_id, target_id)
        await redis_service.set_value(key, move_data)

    async def get_pending_move(self, session_id: str, actor_id: int, target_id: int) -> str | None:
        key = Rk.get_combat_pending_move_key(session_id, actor_id, target_id)
        return await redis_service.get_value(key)

    async def delete_pending_move(self, session_id: str, actor_id: int, target_id: int) -> None:
        key = Rk.get_combat_pending_move_key(session_id, actor_id, target_id)
        await redis_service.delete_key(key)

    async def delete_all_pending_moves_for_actor(self, session_id: str, actor_id: int) -> None:
        pattern = Rk.get_combat_pending_move_pattern(session_id, actor_id)
        # БЫЛО: scan_iter + delete
        # СТАЛО:
        await redis_service.delete_by_pattern(pattern)

    # --- LOGS (List) ---
    async def push_combat_log(self, session_id: str, log_entry_json: str) -> None:
        key = Rk.get_combat_log_key(session_id)
        # БЫЛО: await redis_client.rpush
        # СТАЛО:
        await redis_service.push_to_list(key, log_entry_json)

    async def get_combat_log_list(self, session_id: str) -> list[str]:
        key = Rk.get_combat_log_key(session_id)
        return await redis_service.get_list_range(key)

    # --- PLAYER STATUS ---
    async def set_player_status(self, char_id: int, status: str, ttl: int = 300) -> None:
        key = Rk.get_player_status_key(char_id)
        await redis_service.set_value(key, status, ttl=ttl)

    async def get_player_status(self, char_id: int) -> str | None:
        key = Rk.get_player_status_key(char_id)
        return await redis_service.get_value(key)

    async def delete_player_status(self, char_id: int) -> None:
        key = Rk.get_player_status_key(char_id)
        await redis_service.delete_key(key)


combat_manager = CombatManager()
