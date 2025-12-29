from typing import Any

from apps.common.schemas_dto.combat_source_dto import (
    CombatActionResultDTO,
    CombatDashboardDTO,
    CombatLogDTO,
)
from apps.common.schemas_dto.core_response_dto import CoreResponseDTO
from apps.game_core.core_container import CoreContainer


class CombatRBCClient:
    """
    Клиент для взаимодействия с логикой боя RBC (Reactive Burst Combat).
    Использует новые оркестраторы (Turn, Interaction, Entry).
    Не требует сессии БД для основных операций (Redis-only).
    """

    def __init__(self, core_container: CoreContainer):
        # Получаем оркестраторы из контейнера
        # Они не требуют сессии БД при создании
        self.turn_orchestrator = core_container.get_combat_turn_orchestrator()
        self.interaction_orchestrator = core_container.get_combat_interaction_orchestrator()
        self.core = core_container

    # --- 1. GET SNAPSHOT (Content Message) ---

    async def get_snapshot(self, char_id: int) -> CoreResponseDTO[CombatDashboardDTO]:
        """Запрашивает текущее состояние боя (Snapshot)."""
        return await self.interaction_orchestrator.get_snapshot_wrapped(char_id=char_id)

    # --- 2. GET DATA (Menu Message: Logs, Info) ---

    async def get_data(
        self, char_id: int, data_type: str, params: dict[str, Any]
    ) -> CoreResponseDTO[CombatLogDTO | Any]:
        """Универсальный геттер. Проксирует запрос в Interaction Orchestrator."""
        return await self.interaction_orchestrator.get_data(char_id, data_type, params)

    # --- 3. PERFORM ACTION (Instant Actions: Use Item) ---

    async def perform_action(
        self, char_id: int, action_type: str, payload: dict[str, Any]
    ) -> CoreResponseDTO[CombatActionResultDTO]:
        """Выполняет мгновенное действие. Проксирует запрос в Interaction Orchestrator."""
        return await self.interaction_orchestrator.perform_action(char_id, action_type, payload)

    # --- 4. PROCESS TURN (Submit Turn / Leave) ---

    async def process_turn(
        self, char_id: int, action: str, payload: dict[str, Any]
    ) -> CoreResponseDTO[CombatDashboardDTO]:
        """
        Передает действие фазы хода (удар, выход) в Turn Orchestrator.
        """
        return await self.turn_orchestrator.process_turn(char_id, action, payload)
