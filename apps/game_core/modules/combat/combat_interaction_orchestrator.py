# apps/game_core/modules/combat/combat_interaction_orchestrator.py
from typing import TYPE_CHECKING, Any

from loguru import logger as log

from apps.common.schemas_dto.core_response_dto import CoreResponseDTO, GameStateHeader
from apps.common.schemas_dto.game_state_enum import GameState
from apps.game_core.modules.combat.session.combat_session_service import CombatSessionService

if TYPE_CHECKING:
    from apps.common.schemas_dto.combat_source_dto import (
        CombatActionResultDTO,
        CombatDashboardDTO,
        CombatLogDTO,
    )


class CombatInteractionOrchestrator:
    """
    Легкий оркестратор для обработки запросов чтения и мгновенных действий.
    Работает в связке с CombatRBCClient.

    Маршрутизирует универсальные запросы (get_data, perform_action)
    в конкретные методы CombatSessionService.
    """

    def __init__(self, session_service: CombatSessionService):
        self.session_service = session_service

    async def get_entry_point(self, char_id: int, action: str, context: dict[str, Any]) -> Any:
        """
        Единая точка входа для CoreRouter.
        Возвращает чистый Payload (DTO), без обертки CoreResponseDTO.
        """
        log.info(f"CombatInteraction | action='{action}' char_id={char_id}")

        try:
            if action == "get_snapshot":
                return await self._get_snapshot(char_id)

            elif action == "get_logs":
                page = int(context.get("page", 0))
                return await self._get_logs(char_id, page)

            elif action == "use_item":
                item_id = int(context.get("item_id", 0))
                return await self._use_item(char_id, item_id)

            else:
                log.error(f"CombatInteraction | Unknown action: {action}")
                return None

        except Exception as e:  # noqa: BLE001
            log.exception(f"CombatInteraction | Error processing {action}: {e}")
            return None

    # --- Public Client Facade (Returns CoreResponseDTO) ---

    async def get_snapshot(self, char_id: int) -> CoreResponseDTO:
        """
        Прямой вызов дашборда (для клиента).
        """
        snapshot_dto = await self._get_snapshot(char_id)
        return CoreResponseDTO(header=GameStateHeader(current_state=GameState.COMBAT), payload=snapshot_dto)

    async def get_data(self, char_id: int, data_type: str, params: dict[str, Any]) -> CoreResponseDTO:
        """
        Маршрутизатор типов данных (для клиента).
        """
        payload = None

        if data_type == "logs":
            page = int(params.get("page", 0))
            payload = await self._get_logs(char_id, page)

        elif data_type == "target_info":
            # TODO: Implement target info
            pass

        else:
            return CoreResponseDTO(
                header=GameStateHeader(current_state=GameState.COMBAT, error=f"Unknown data_type: {data_type}"),
                payload=None,
            )

        return CoreResponseDTO(header=GameStateHeader(current_state=GameState.COMBAT), payload=payload)

    async def perform_action(self, char_id: int, action_type: str, payload: dict[str, Any]) -> CoreResponseDTO:
        """
        Проксирует действие в сервис (для клиента).
        """
        result_dto = None

        if action_type == "use_item":
            item_id = int(payload.get("item_id", 0))
            result_dto = await self._use_item(char_id, item_id)

        else:
            return CoreResponseDTO(
                header=GameStateHeader(current_state=GameState.COMBAT, error=f"Unknown action_type: {action_type}"),
                payload=None,
            )

        return CoreResponseDTO(header=GameStateHeader(current_state=GameState.COMBAT), payload=result_dto)

    # --- Private Business Logic (Returns Pure DTO) ---

    async def _get_snapshot(self, char_id: int) -> "CombatDashboardDTO":
        return await self.session_service.get_snapshot(char_id)

    async def _get_logs(self, char_id: int, page: int) -> "CombatLogDTO":
        return await self.session_service.get_logs(char_id, page)

    async def _use_item(self, char_id: int, item_id: int) -> "CombatActionResultDTO":
        return await self.session_service.use_item(char_id, item_id)
