# apps/game_core/modules/exploration/exploration_orchestrator.py
from typing import Any

from apps.common.schemas_dto.auth_dto import GameStage
from apps.common.schemas_dto.exploration_dto import EncounterDTO, WorldNavigationDTO
from apps.common.services.redis.manager.account_manager import AccountManager
from apps.common.services.redis.manager.world_manager import WorldManager
from apps.game_core.modules.exploration.encounter_service import EncounterService
from apps.game_core.modules.exploration.game_world_service import GameWorldService
from apps.game_core.modules.exploration.movement_service import MovementService

DEFAULT_SPAWN_POINT = "52_52"


class ExplorationOrchestrator:
    """
    Оркестратор процесса исследования мира.
    """

    def __init__(
        self,
        game_world_service: GameWorldService,
        account_manager: AccountManager,
        world_manager: WorldManager,
        encounter_service: EncounterService,
        movement_service: MovementService,
    ):
        self.game_world_svc = game_world_service
        self.account_mgr = account_manager
        self.world_mgr = world_manager
        self.encounter_svc = encounter_service
        self.movement_svc = movement_service

    async def move_and_explore(self, char_id: int, target_loc_id: str) -> EncounterDTO | WorldNavigationDTO | None:
        move_result = await self.movement_svc.execute_move(char_id, target_loc_id)

        if not move_result:
            return None

        nav_data = move_result["nav_data"]
        travel_time = move_result["travel_time"]

        encounter = await self.encounter_svc.calculate_encounter(char_id, nav_data, target_loc_id)

        if encounter:
            await self.account_mgr.update_account_fields(char_id, {"game_stage": GameStage.EXPLORATION_PENDING})
            encounter.metadata["travel_time"] = travel_time
            return encounter

        return await self._assemble_navigation_dto(char_id, target_loc_id, nav_data, travel_time)

    async def get_current_location_data(self, char_id: int) -> WorldNavigationDTO | None:
        account_data = await self.account_mgr.get_account_data(char_id)
        if not account_data:
            return None

        loc_id = account_data.get("location_id", DEFAULT_SPAWN_POINT)

        nav_data = await self.game_world_svc.get_location_for_navigation(loc_id)
        if not nav_data:
            return None

        return await self._assemble_navigation_dto(char_id, loc_id, nav_data, travel_time=0.0)

    async def _assemble_navigation_dto(
        self, char_id: int, loc_id: str, nav_data: dict[str, Any], travel_time: float
    ) -> WorldNavigationDTO:
        players_set = await self.world_mgr.get_players_in_location(loc_id)
        players_set.discard(str(char_id))

        visual_objects = []
        service_key = nav_data.get("service")
        if service_key:
            visual_objects.append(f"Объект: {service_key}")

        return WorldNavigationDTO(
            loc_id=loc_id,
            name=nav_data.get("name", "???"),
            description=nav_data.get("description", "..."),
            exits=nav_data.get("exits", {}),
            flags=nav_data.get("flags", {}),  # Берем флаги как есть
            players_count=len(players_set),
            active_battles=0,
            visual_objects=visual_objects,
            metadata={"travel_time": travel_time},
        )
