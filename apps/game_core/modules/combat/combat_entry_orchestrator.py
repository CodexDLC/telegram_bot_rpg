from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.schemas_dto.combat_source_dto import CombatDashboardDTO
from apps.common.schemas_dto.core_response_dto import CoreResponseDTO, GameStateHeader
from apps.common.schemas_dto.game_state_enum import GameState
from apps.game_core.modules.combat.session.initialization.combat_lifecycle_service import CombatLifecycleService
from apps.game_core.modules.combat.session.runtime.combat_view_service import CombatViewService

if TYPE_CHECKING:
    from apps.game_core.modules.combat.session.combat_session_service import CombatSessionService


class CombatEntryOrchestrator:
    """
    Оркестратор входа в бой и инициализации.
    Отвечает за создание сессии, загрузку участников и формирование первого ответа.
    """

    def __init__(
        self,
        lifecycle_service: CombatLifecycleService,
        session_service: "CombatSessionService",
        view_service: CombatViewService,
        db_session: AsyncSession,
    ):
        self.lifecycle = lifecycle_service
        self.session_service = session_service
        self.view_service = view_service
        self.db_session = db_session

    async def initialize_pve(self, char_id: int, monster_id: str) -> CoreResponseDTO[CombatDashboardDTO]:
        """
        Инициализирует PvE бой (Игрок vs Монстр).
        """
        # 1. Создаем сессию (Lifecycle)
        session_id = await self.lifecycle.start_pve_battle(char_id, monster_id, self.db_session)

        if not session_id:
            return CoreResponseDTO(
                header=GameStateHeader(current_state=GameState.EXPLORATION, error="Failed to start battle"),
                payload=None,
            )

        # 2. Получаем Snapshot (View)
        # SessionService сам найдет активную сессию по char_id
        snapshot = await self.session_service.get_snapshot(char_id)

        if not snapshot:
            return CoreResponseDTO(
                header=GameStateHeader(current_state=GameState.EXPLORATION, error="Failed to get battle snapshot"),
                payload=None,
            )

        return CoreResponseDTO(header=GameStateHeader(current_state=GameState.COMBAT), payload=snapshot)

    async def restore_active_battles(self) -> None:
        """
        Восстанавливает активные бои после перезагрузки (заглушка).
        """
        # TODO: Реализовать восстановление супервизоров для активных сессий из Redis
        pass
