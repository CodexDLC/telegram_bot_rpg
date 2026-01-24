# apps/bot/core_client/exploration.py

from apps.common.schemas_dto.exploration_dto import EncounterDTO, WorldNavigationDTO
from apps.game_core.modules.exploration.exploration_orchestrator import ExplorationOrchestrator


class ExplorationClient:
    """
    Клиент-адаптер для взаимодействия UI-слоя с Ядром (Game Core) в части исследования мира.
    """

    def __init__(self, orchestrator: ExplorationOrchestrator):
        self._orchestrator = orchestrator

    async def move(self, char_id: int, target_loc_id: str) -> EncounterDTO | WorldNavigationDTO | None:
        """
        Выполняет перемещение и исследование.
        """
        return await self._orchestrator.move_and_explore(char_id, target_loc_id)

    async def get_current_location(self, char_id: int) -> WorldNavigationDTO | None:
        """
        Запрашивает данные о текущей локации персонажа.
        """
        return await self._orchestrator.get_current_location_data(char_id)
