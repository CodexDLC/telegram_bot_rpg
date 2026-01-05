# apps/game_core/modules/combat/combat_turn_orchestrator.py
from typing import TYPE_CHECKING, Any

from apps.common.schemas_dto.core_response_dto import CoreResponseDTO, GameStateHeader
from apps.common.schemas_dto.game_state_enum import GameState

if TYPE_CHECKING:
    from apps.common.schemas_dto.combat_source_dto import CombatDashboardDTO
    from apps.game_core.modules.combat.session.combat_session_service import CombatSessionService


class CombatTurnOrchestrator:
    """
    Тяжелый движок (Turn Engine).
    Роль: Обработка хода игрока ("Спусковой крючок"). Отвечает за асинхронный запуск механик.
    Клиент: CombatRBCClient (метод process_turn).
    """

    def __init__(
        self,
        session_service: "CombatSessionService",
    ):
        self.session_service = session_service

    async def process_turn(self, char_id: int, action: str, payload: dict[str, Any]) -> CoreResponseDTO:
        """
        Универсальный метод обработки действий фазы хода.
        Диспетчеризирует action в приватные методы.
        """
        if action == "submit":
            return await self._register_move(char_id, payload)
        elif action == "leave":
            return await self._leave_battle(char_id)
        else:
            return CoreResponseDTO(
                header=GameStateHeader(current_state=GameState.COMBAT, error=f"Unknown turn action: {action}"),
                payload=None,
            )

    async def _register_move(self, char_id: int, move_data: dict[str, Any]) -> CoreResponseDTO["CombatDashboardDTO"]:
        """
        Регистрация хода (удар/блок).
        """
        # 1. Регистрируем ход через сервис
        await self.session_service.register_move(char_id, move_data)

        # 2. Получаем актуальное состояние (Snapshot)
        snapshot_dto = await self.session_service.get_snapshot(char_id)

        return CoreResponseDTO(header=GameStateHeader(current_state=GameState.COMBAT), payload=snapshot_dto)

    async def _leave_battle(self, char_id: int) -> CoreResponseDTO:
        """
        Выход из боя (после победы/поражения).
        """
        # TODO: Реализовать полноценный сервис финализации (FinalizeService).
        # Он должен:
        # 1. Проверять prev_state в Redis (ac:{id}).
        # 2. Определять контекст выхода (победа/смерть/бегство).
        # 3. Возвращать правильный GameState (LOBBY, EXPLORATION, etc.).

        # Пока заглушка: возвращаем в Лобби.
        return CoreResponseDTO(header=GameStateHeader(current_state=GameState.LOBBY), payload=None)
