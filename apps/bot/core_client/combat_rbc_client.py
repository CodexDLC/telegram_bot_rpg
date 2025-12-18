from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.schemas_dto.combat_source_dto import CombatDashboardDTO
from apps.common.services.core_service.manager.account_manager import AccountManager
from apps.common.services.core_service.manager.combat_manager import CombatManager
from apps.game_core.game_service.combat.combat_orchestrator_rbc import CombatOrchestratorRBC


class CombatRBCClient:
    """
    Клиент для взаимодействия с логикой боя RBC (Reactive Burst Combat).
    В текущей реализации (монолит) он напрямую вызывает CombatOrchestratorRBC.
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
        # Теперь здесь возвращается CombatDashboardDTO, а не str
        return await self._orchestrator.start_battle(players, enemies)

    async def register_move(self, session_id: str, char_id: int, target_id: int, move_data: dict) -> CombatDashboardDTO:
        """
        Передает ход в Ядро и возвращает Snapshot.
        """
        return await self._orchestrator.register_move(session_id, char_id, target_id, move_data)

    async def get_next_target(self, session_id: str, char_id: int) -> dict | None:
        """
        Запрашивает следующую цель для атаки из очереди.
        """
        return await self._orchestrator.get_next_target(session_id, char_id)

    async def get_full_state(self, session_id: str, char_id: int) -> dict:
        """
        Запрашивает полное состояние боя для перерисовки UI.
        """
        return await self._orchestrator.get_full_state(session_id, char_id)

    async def get_logs(self, session_id: str, limit: int = 10) -> list[str]:
        """
        Запрашивает последние N записей из лога боя.
        """
        return await self._orchestrator.get_logs(session_id, limit)

    async def check_battle_status(self, session_id: str) -> str:
        """
        Проверяет текущий статус боя (активен, победа, поражение).
        """
        return await self._orchestrator.check_battle_status(session_id)

    async def get_snapshot(self, session_id: str, char_id: int) -> CombatDashboardDTO:
        """Просто запрашивает текущее состояние (для Refresh)."""
        return await self._orchestrator.get_dashboard_snapshot(session_id, char_id)
