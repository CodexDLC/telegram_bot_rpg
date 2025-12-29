from typing import TYPE_CHECKING, Any

from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.schemas_dto.game_state_enum import GameState
from apps.game_core.system.protocols import CoreOrchestratorProtocol

if TYPE_CHECKING:
    from apps.game_core.core_container import CoreContainer


class CoreRouter:
    """
    Маршрутизатор запросов между модулями (Core Layer).
    Позволяет одному оркестратору вызвать другой (переход между состояниями).
    """

    def __init__(self, container: "CoreContainer"):
        self.container = container

    async def get_initial_view(
        self,
        target_state: str,
        char_id: int,
        session: AsyncSession,
        action: str = "initialize",
        context: dict[str, Any] | None = None,
    ) -> Any:
        """
        Запрашивает начальное состояние (View) у целевого модуля.
        Возвращает payload (данные), а не полный DTO.
        Обертку в CoreResponseDTO должен делать вызывающий код.
        """
        context = context or {}
        log.info(f"CoreRouter | transition char_id={char_id} to={target_state} action={action}")

        # Получаем оркестратор
        orchestrator = self._get_orchestrator(target_state, session)

        if not isinstance(orchestrator, CoreOrchestratorProtocol):
            # Fallback: если протокол не реализован, возвращаем контекст как заглушку
            log.warning(f"CoreRouter | Orchestrator for {target_state} does not implement CoreOrchestratorProtocol")
            return context

        # Вызываем единую точку входа и возвращаем чистый payload
        return await orchestrator.get_entry_point(char_id, action, context)

    def _get_orchestrator(self, state: str, session: AsyncSession) -> Any:
        """
        Возвращает оркестратор для указанного стейта.
        """
        if state == GameState.SCENARIO:
            return self.container.get_scenario_core_orchestrator(session)
        elif state == GameState.LOBBY:
            return self.container.get_lobby_core_orchestrator(session)
        elif state == GameState.ONBOARDING:
            return self.container.get_onboarding_core_orchestrator(session)
        elif state == GameState.INVENTORY:
            return self.container.get_inventory_core_orchestrator(session)
        elif state == GameState.EXPLORATION:
            return self.container.get_exploration_core_orchestrator(session)
        # elif state == GameState.COMBAT:
        #     return self.container.get_combat_core_orchestrator(session)

        # TODO: Добавить Arena

        raise ValueError(f"Unknown state for router: {state}")
