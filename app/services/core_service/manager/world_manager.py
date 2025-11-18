# app/services/core_service/managers/world_manager.py
from app.services.core_service.redis_key import RedisKeys as Rk
from app.services.core_service.redis_service import redis_service


class WorldManager:
    """
    CRUD-Менеджер (Репозиторий) для ключей 'world:*'.
    Не содержит бизнес-логики.
    """

    async def write_location_meta(self, loc_id: str, data: dict) -> None:
        """Записывает данные в хеш 'world:loc:<loc_id>'."""
        key = Rk.get_world_location_meta_key(loc_id)
        await redis_service.set_hash_fields(key, data)

    async def get_location_meta(self, loc_id: str) -> dict | None:
        """Читает *все* данные из хеша 'world:loc:<loc_id>'."""
        key = Rk.get_world_location_meta_key(loc_id)
        return await redis_service.get_all_hash(key)

    async def location_meta_exists(self, loc_id: str) -> bool:
        """Проверяет, существует ли ключ 'world:loc:<loc_id>'."""
        key = Rk.get_world_location_meta_key(loc_id)
        return await redis_service.key_exists(key)

    # --- Методы для 'world:players_loc:*' (Списки игроков) ---

    async def add_player_to_location(self, loc_id: str, char_id: int) -> None:
        """Добавляет игрока в 'world:players_loc:<loc_id>' (Set)."""
        key = Rk.get_world_location_players_key(loc_id)
        await redis_service.add_to_set(key, char_id)

    async def remove_player_from_location(self, loc_id: str, char_id: int) -> None:
        """Удаляет игрока из 'world:players_loc:<loc_id>' (Set)."""
        key = Rk.get_world_location_players_key(loc_id)
        await redis_service.remove_from_set(key, char_id)

    async def get_players_in_location(self, loc_id: str) -> set:
        """Получает *всех* игроков из 'world:players_loc:<loc_id>' (Set)."""
        key = Rk.get_world_location_players_key(loc_id)
        return await redis_service.get_to_set(key)


world_manager = WorldManager()
