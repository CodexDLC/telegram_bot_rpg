from typing import Any

from apps.common.schemas_dto.combat_source_dto import (
    CombatDashboardDTO,
    CombatLogDTO,
)
from apps.common.schemas_dto.core_response_dto import CoreResponseDTO
from apps.game_core.core_container import CoreContainer


class CombatRBCClient:
    """
    Клиент для взаимодействия с логикой боя RBC (Reactive Burst Combat).
    Использует CombatGateway как единую точку входа (имитация HTTP-клиента).
    """

    def __init__(self, core_container: CoreContainer):
        # Получаем Gateway из контейнера
        self.gateway = core_container.get_combat_gateway()
        self.core = core_container

    # --- UNIVERSAL API (Future HTTP Client) ---

    async def handle_action(
        self, char_id: int, action: str, payload: dict[str, Any]
    ) -> CoreResponseDTO[CombatDashboardDTO]:
        """
        Отправляет действие (POST /combat/action).
        Возвращает обновленный Dashboard.
        """
        return await self.gateway.handle_action(char_id, action, payload)

    async def get_view(
        self, char_id: int, view_type: str, params: dict[str, Any]
    ) -> CoreResponseDTO[CombatDashboardDTO | CombatLogDTO]:
        """
        Запрашивает данные (GET /combat/view).
        """
        return await self.gateway.get_view(char_id, view_type, params)

    # --- LEGACY ALIASES (For compatibility with Bot Orchestrator) ---
    # Эти методы можно удалить после рефакторинга Bot Orchestrator,
    # но пока оставим их как прокси к новым методам.

    async def get_snapshot(self, char_id: int) -> CoreResponseDTO[CombatDashboardDTO]:
        return await self.get_view(char_id, "snapshot", {})

    async def get_data(
        self, char_id: int, data_type: str, params: dict[str, Any]
    ) -> CoreResponseDTO[CombatLogDTO | Any]:
        return await self.get_view(char_id, data_type, params)

    async def perform_action(
        self, char_id: int, action_type: str, payload: dict[str, Any]
    ) -> CoreResponseDTO[CombatDashboardDTO]:
        """
        Теперь возвращает Dashboard, а не ActionResult!
        """
        return await self.handle_action(char_id, action_type, payload)

    async def process_turn(
        self, char_id: int, action: str, payload: dict[str, Any]
    ) -> CoreResponseDTO[CombatDashboardDTO]:
        return await self.handle_action(char_id, action, payload)
