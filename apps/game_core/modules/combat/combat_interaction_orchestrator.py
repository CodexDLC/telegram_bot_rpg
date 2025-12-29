from typing import Any

from apps.common.schemas_dto.core_response_dto import CoreResponseDTO, GameStateHeader
from apps.common.schemas_dto.game_state_enum import GameState
from apps.game_core.modules.combat.session.combat_session_service import CombatSessionService


class CombatInteractionOrchestrator:
    """
    Легкий оркестратор для обработки запросов чтения и мгновенных действий.
    Работает в связке с CombatRBCClient.

    Маршрутизирует универсальные запросы (get_data, perform_action)
    в конкретные методы CombatSessionService.
    """

    def __init__(self, session_service: CombatSessionService):
        self.session_service = session_service

    # --- 1. SNAPSHOT (Content) ---

    async def get_snapshot_wrapped(self, char_id: int) -> CoreResponseDTO:
        """
        Прямой вызов дашборда.
        """
        # SessionService сам зарезолвит ID и вернет DTO
        snapshot_dto = await self.session_service.get_snapshot(char_id)
        return CoreResponseDTO(header=GameStateHeader(current_state=GameState.COMBAT), payload=snapshot_dto)

    # --- 2. GET DATA (Menu: Logs, Info, etc.) ---

    async def get_data(self, char_id: int, data_type: str, params: dict[str, Any]) -> CoreResponseDTO:
        """
        Маршрутизатор типов данных.
        Превращает строковый data_type в вызов конкретного метода сервиса.
        """
        payload = None

        if data_type == "logs":
            # Извлекаем параметры для логов
            page = int(params.get("page", 0))
            payload = await self.session_service.get_logs(char_id, page)

        elif data_type == "target_info":
            # Заготовка под просмотр инфо о враге
            # target_id = params.get("target_id")
            # payload = await self.session_service.get_target_info(char_id, target_id)
            pass

        else:
            return CoreResponseDTO(
                header=GameStateHeader(current_state=GameState.COMBAT, error=f"Unknown data_type: {data_type}"),
                payload=None,
            )

        return CoreResponseDTO(header=GameStateHeader(current_state=GameState.COMBAT), payload=payload)

    # --- 3. PERFORM ACTION (Instant: Items, Tactics) ---

    async def perform_action(self, char_id: int, action_type: str, payload: dict[str, Any]) -> CoreResponseDTO:
        """
        Проксирует действие в сервис.
        Диспетчеризирует action_type в конкретные методы сервиса.
        """
        result_dto = None

        if action_type == "use_item":
            item_id = int(payload.get("item_id", 0))
            result_dto = await self.session_service.use_item(char_id, item_id)

        # elif action_type == "switch_target":
        #     target_id = int(payload.get("target_id", 0))
        #     result_dto = await self.session_service.switch_target(char_id, target_id)

        else:
            return CoreResponseDTO(
                header=GameStateHeader(current_state=GameState.COMBAT, error=f"Unknown action_type: {action_type}"),
                payload=None,
            )

        return CoreResponseDTO(header=GameStateHeader(current_state=GameState.COMBAT), payload=result_dto)
