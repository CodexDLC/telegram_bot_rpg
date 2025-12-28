from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.schemas_dto.combat_source_dto import (
    CombatActionResultDTO,
    CombatDashboardDTO,
    CombatLogDTO,
)
from apps.common.schemas_dto.core_response_dto import CoreResponseDTO
from apps.common.services.core_service.manager.account_manager import AccountManager
from apps.common.services.core_service.manager.combat_manager import CombatManager
from apps.game_core.game_service.combat.combat_orchestrator_rbc import CombatOrchestratorRBC


class CombatRBCClient:
    """
    Клиент для взаимодействия с логикой боя RBC (Reactive Burst Combat).
    Тонкий прокси к Core Orchestrator.
    """

    def __init__(
        self,
        session: AsyncSession,
        account_manager: AccountManager,
        combat_manager: CombatManager,
    ):
        self._orchestrator = CombatOrchestratorRBC(session, combat_manager, account_manager)

    # --- 1. GET SNAPSHOT (Content Message) ---

    async def get_snapshot(self, char_id: int) -> CoreResponseDTO[CombatDashboardDTO]:
        """Запрашивает текущее состояние боя (Snapshot)."""
        # Вызываем обертку в Core, которая возвращает CoreResponseDTO
        return await self._orchestrator.get_snapshot_wrapped(char_id=char_id)

    # --- 2. GET DATA (Menu Message: Logs, Info) ---

    async def get_data(
        self, char_id: int, data_type: str, params: dict[str, Any]
    ) -> CoreResponseDTO[CombatLogDTO | Any]:
        """Универсальный геттер. Проксирует запрос в Core."""
        return await self._orchestrator.get_data(char_id, data_type, params)

    # --- 3. PERFORM ACTION (Instant Actions: Use Item) ---

    async def perform_action(
        self, char_id: int, action_type: str, payload: dict[str, Any]
    ) -> CoreResponseDTO[CombatActionResultDTO]:
        """Выполняет мгновенное действие. Проксирует запрос в Core."""
        return await self._orchestrator.perform_action(char_id, action_type, payload)

    # --- 4. REGISTER MOVE (Submit Turn) ---

    async def register_move(self, char_id: int, target_id: int, move_data: dict) -> CoreResponseDTO[CombatDashboardDTO]:
        """Передает ход в Ядро."""
        return await self._orchestrator.register_move_wrapped(char_id=char_id, target_id=target_id, move_data=move_data)
