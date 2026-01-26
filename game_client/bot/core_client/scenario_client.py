from typing import TYPE_CHECKING

from common.schemas.response import CoreResponseDTO
from common.schemas.scenario import ScenarioPayloadDTO



class ScenarioClient:
    """
    Клиент-адаптер для взаимодействия UI-слоя с ScenarioCoreOrchestrator.
    Использует CoreContainer для доступа к бэкенду и управления сессией БД.
    """

    def __init__(self, core_container: "CoreContainer"):
        self.core = core_container

    async def initialize_scenario(
        self, char_id: int, quest_key: str, prev_state: str | None = None, prev_loc: str | None = None
    ) -> CoreResponseDTO[ScenarioPayloadDTO]:
        """
        Запускает новый сценарий для персонажа.
        """
        async with self.core.get_session_context() as session:
            orchestrator = self.core.get_scenario_core_orchestrator(session)
            return await orchestrator.initialize_scenario(char_id, quest_key, prev_state, prev_loc)

    async def step_scenario(self, char_id: int, action_id: str) -> CoreResponseDTO[ScenarioPayloadDTO]:
        """
        Выполняет следующий шаг в сценарии.
        """
        async with self.core.get_session_context() as session:
            orchestrator = self.core.get_scenario_core_orchestrator(session)
            return await orchestrator.step_scenario(char_id, action_id)

    async def resume_scenario(self, char_id: int) -> CoreResponseDTO[ScenarioPayloadDTO]:
        """
        Восстанавливает прерванную сессию сценария.
        """
        async with self.core.get_session_context() as session:
            orchestrator = self.core.get_scenario_core_orchestrator(session)
            return await orchestrator.resume_scenario(char_id)

    async def finalize_scenario(self, char_id: int) -> CoreResponseDTO:
        """
        Завершает сценарий.
        """
        async with self.core.get_session_context() as session:
            orchestrator = self.core.get_scenario_core_orchestrator(session)
            return await orchestrator.finalize_scenario(char_id)
