# apps/game_core/modules/exploration/movement_service.py
from typing import Any

from loguru import logger as log

from apps.common.services.redis.manager.account_manager import AccountManager
from apps.common.services.redis.manager.world_manager import WorldManager
from apps.game_core.modules.exploration.game_world_service import GameWorldService


class MovementService:
    """
    Сервис, отвечающий ИСКЛЮЧИТЕЛЬНО за физическое перемещение персонажа.
    """

    def __init__(
        self,
        world_manager: WorldManager,
        account_manager: AccountManager,
        game_world_service: GameWorldService,
    ):
        self.world_mgr = world_manager
        self.account_mgr = account_manager
        self.game_world_svc = game_world_service

    async def execute_move(self, char_id: int, target_loc_id: str) -> dict[str, Any] | None:
        """
        Выполняет перемещение игрока.
        Возвращает словарь с nav_data и travel_time.
        """
        # 1. Проверка существования целевой локации
        nav_data = await self.game_world_svc.get_location_for_navigation(target_loc_id)
        if not nav_data:
            log.warning(f"MovementService | Move failed. Target location not found: {target_loc_id}")
            return None

        # 2. Получение текущей локации для расчета времени
        account_data = await self.account_mgr.get_account_data(char_id)
        current_loc_id = account_data.get("location_id") if account_data else None

        # 3. Расчет времени перехода
        travel_time = 0.0
        if current_loc_id:
            current_loc_data = await self.game_world_svc.get_location_for_navigation(current_loc_id)
            if current_loc_data:
                exits = current_loc_data.get("exits", {})
                full_target_key = f"nav:{target_loc_id}"
                target_exit = exits.get(full_target_key) or exits.get(target_loc_id)
                if target_exit and isinstance(target_exit, dict):
                    travel_time = float(target_exit.get("time_duration", 0))

        # 4. Обновление Redis и БД
        if current_loc_id:
            await self.world_mgr.remove_player_from_location(current_loc_id, char_id)

        await self.world_mgr.add_player_to_location(target_loc_id, char_id)

        await self.account_mgr.update_account_fields(
            char_id,
            {"location_id": target_loc_id, "prev_location_id": current_loc_id},
        )

        return {"nav_data": nav_data, "travel_time": travel_time}
