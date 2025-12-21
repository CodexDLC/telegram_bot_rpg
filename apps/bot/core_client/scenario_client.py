from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.database.repositories.ORM.scenario_repository import ScenarioRepositoryORM
from apps.common.schemas_dto.scenario_dto import ScenarioResponseDTO
from apps.common.services.core_service.manager.account_manager import AccountManager
from apps.common.services.core_service.redis_service import RedisService
from apps.game_core.game_service.quest.logic.scenario_director import ScenarioDirector
from apps.game_core.game_service.quest.logic.scenario_evaluator import ScenarioEvaluator
from apps.game_core.game_service.quest.logic.scenario_formatter import ScenarioFormatter
from apps.game_core.game_service.quest.logic.scenario_manager import ScenarioManager
from apps.game_core.game_service.quest.scenario_core_orchestrator import ScenarioCoreOrchestrator


class ScenarioClient:
    """
    Клиент-адаптер для взаимодействия UI-слоя с ScenarioCoreOrchestrator.
    Предоставляет простой интерфейс для управления жизненным циклом сценариев.
    """

    def __init__(self, session: AsyncSession, redis_service: RedisService, account_manager: AccountManager):
        # Инициализация зависимостей Core-слоя
        repo = ScenarioRepositoryORM(session)
        manager = ScenarioManager(redis_service)
        evaluator = ScenarioEvaluator()
        director = ScenarioDirector(evaluator)
        formatter = ScenarioFormatter()

        self._orchestrator = ScenarioCoreOrchestrator(
            repo=repo,
            account_manager=account_manager,
            scenario_manager=manager,
            scenario_evaluator=evaluator,
            scenario_director=director,
            scenario_formatter=formatter,
        )

    async def initialize_scenario(
        self, char_id: int, quest_key: str, prev_state: str | None = None, prev_loc: str | None = None
    ) -> ScenarioResponseDTO:
        """
        Запускает новый сценарий для персонажа.
        """
        return await self._orchestrator.initialize_scenario(char_id, quest_key, prev_state, prev_loc)

    async def step_scenario(self, char_id: int, action_id: str) -> ScenarioResponseDTO:
        """
        Выполняет следующий шаг в сценарии на основе выбора игрока.
        """
        return await self._orchestrator.step_scenario(char_id, action_id)

    async def resume_scenario(self, char_id: int) -> ScenarioResponseDTO:
        """
        Восстанавливает прерванную сессию сценария.
        """
        return await self._orchestrator.resume_scenario(char_id)

    async def finalize_scenario(self, char_id: int) -> dict[str, Any]:
        """
        Завершает сценарий и экспортирует результаты.
        """
        return await self._orchestrator.finalize_scenario(char_id)
