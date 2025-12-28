# apps/game_core/game_service/scenario_orchestrator/handlers/base_handler.py
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.schemas_dto.core_response_dto import CoreResponseDTO
from apps.common.services.core_service.manager.account_manager import AccountManager

if TYPE_CHECKING:
    from apps.game_core.game_service.core_router import CoreRouter
    from apps.game_core.game_service.scenario_orchestrator.logic.scenario_manager import ScenarioManager


class BaseScenarioHandler(ABC):
    """
    Абстрактный контракт для любого сценария.
    Определяет методы, которые обязан реализовать каждый обработчик квеста.
    """

    def __init__(self, manager: "ScenarioManager", account_manager: AccountManager, db_session: AsyncSession):
        self.manager = manager
        self.am = account_manager
        self.db = db_session

    @abstractmethod
    async def on_initialize(
        self, char_id: int, quest_master: dict[str, Any], prev_state: str | None = None, prev_loc: str | None = None
    ) -> dict[str, Any]:
        """
        Логика старта сценария.
        Должен:
        1. Подготовить данные (контекст).
        2. Зарегистрировать сессию (через manager).
        3. Вернуть готовый контекст.
        """
        pass

    @abstractmethod
    async def on_finalize(self, char_id: int, context: dict[str, Any], router: "CoreRouter") -> CoreResponseDTO:
        """
        Логика завершения сценария.
        Должен:
        1. Перенести накопленные данные из контекста в постоянное хранилище.
        2. Использовать router для перехода в следующий стейт.
        3. Вернуть CoreResponseDTO.
        """
        pass
