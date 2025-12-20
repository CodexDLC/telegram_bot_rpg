from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.schemas_dto.combat_source_dto import CombatDashboardDTO
from apps.common.services.core_service.manager.account_manager import AccountManager
from apps.common.services.core_service.manager.combat_manager import CombatManager
from apps.game_core.game_service.combat.combat_orchestrator_rbc import CombatOrchestratorRBC


class CombatRBCClient:
    """
    Клиент для взаимодействия с логикой боя RBC (Reactive Burst Combat).
    Очищенная версия: предоставляет только методы для действий и получения единого снимка состояния (Snapshot).
    """

    def __init__(
        self,
        session: AsyncSession,
        account_manager: AccountManager,
        combat_manager: CombatManager,
    ):
        self._orchestrator = CombatOrchestratorRBC(session, combat_manager, account_manager)

    async def start_battle(self, players: list[int], enemies: list[int]) -> CombatDashboardDTO:
        """
        Запрашивает создание новой боевой сессии и возвращает стартовый Snapshot.
        """
        return await self._orchestrator.start_battle(players, enemies)

    async def register_move(self, session_id: str, char_id: int, target_id: int, move_data: dict) -> CombatDashboardDTO:
        """
        Передает ход в Ядро и возвращает обновленный Snapshot.
        """
        return await self._orchestrator.register_move(session_id, char_id, target_id, move_data)

    async def get_snapshot(self, session_id: str, char_id: int) -> CombatDashboardDTO:
        """
        Запрашивает текущее состояние боя (Snapshot) для обновления UI.
        """
        return await self._orchestrator.get_dashboard_snapshot(session_id, char_id)

    async def use_consumable(self, session_id: str, char_id: int, item_id: int) -> tuple[bool, str]:
        """
        Использует расходник в бою.
        """
        return await self._orchestrator.use_consumable(session_id, char_id, item_id)
