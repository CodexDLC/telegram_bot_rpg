# apps/game_core/modules/combat/session/combat_session_service.py
"""
Файл: app/game_core/modules/combat/session/combat_session_service.py
"""

from apps.common.schemas_dto.combat_source_dto import (
    CombatActionResultDTO,
    CombatDashboardDTO,
    CombatLogDTO,
)
from apps.common.services.core_service.manager.account_manager import AccountManager
from apps.common.services.core_service.manager.combat_manager import CombatManager
from apps.common.services.core_service.redis_fields import AccountFields as Af

# Импорты зависимостей (Менеджеров)
from apps.game_core.modules.combat.mechanics.combat_consumable_service import CombatConsumableService
from apps.game_core.modules.combat.session.runtime.combat_turn_manager import CombatTurnManager
from apps.game_core.modules.combat.session.runtime.combat_view_service import CombatViewService


class CombatSessionService:
    """
    Единая точка входа (Facade) для выполнения операций в бою.
    1. Резолвит session_id по char_id.
    2. Загружает данные через CombatManager.
    3. Делегирует маппинг в CombatViewService.
    """

    def __init__(
        self,
        account_manager: AccountManager,
        combat_manager: CombatManager,
        turn_manager: CombatTurnManager,
        view_service: CombatViewService,
        consumable_service: CombatConsumableService,
    ):
        self.account_manager = account_manager
        self.combat_manager = combat_manager
        self.turn_manager = turn_manager
        self.view_service = view_service
        self.consumable_service = consumable_service

    # --- INTERNAL RESOLVER ---

    async def _resolve_session_id(self, char_id: int) -> str:
        """Приватный резолв. Кидает ошибку, если боя нет."""
        session_id = await self.account_manager.get_account_field(char_id, Af.COMBAT_SESSION_ID)
        if not session_id:
            raise ValueError(f"Character {char_id} is not in active combat.")
        return str(session_id)

    # --- PUBLIC API ---

    async def get_snapshot(self, char_id: int) -> CombatDashboardDTO:
        """Получить экран боя."""
        session_id = await self._resolve_session_id(char_id)

        # 1. Загружаем сырые данные
        meta = await self.combat_manager.get_rbc_session_meta(session_id)
        if not meta:
            raise ValueError(f"Session {session_id} meta not found")

        actors_data = await self.combat_manager.get_rbc_all_actors_json(session_id)
        if not actors_data:
            raise ValueError(f"Session {session_id} actors not found")

        queue_list = await self.combat_manager.get_exchange_queue_list(session_id, char_id)

        # 2. Строим DTO через ViewService
        return self.view_service.build_dashboard_dto(session_id, char_id, meta, actors_data, queue_list)

    async def get_logs(self, char_id: int, page: int = 0) -> CombatLogDTO:
        """Получить логи."""
        session_id = await self._resolve_session_id(char_id)

        raw_logs = await self.combat_manager.get_combat_log_list(session_id)

        return self.view_service.build_logs_dto(raw_logs, page)

    async def register_move(self, char_id: int, move_dto: dict) -> None:
        """Сделать ход (Удар/Блок)."""
        session_id = await self._resolve_session_id(char_id)
        # Делегируем TurnManager
        await self.turn_manager.register_move_request(session_id, char_id, move_dto)

    async def use_item(self, char_id: int, item_id: int) -> CombatActionResultDTO:
        """Использовать предмет (Мгновенное действие)."""
        session_id = await self._resolve_session_id(char_id)
        # Делегируем ConsumableService (Mechanics)
        return await self.consumable_service.use_item(session_id, char_id, item_id)

    # --- SESSION MANAGEMENT (Facade for AccountManager) ---

    async def link_players_to_session(self, char_ids: list[int], session_id: str) -> None:
        """
        Привязывает игроков к боевой сессии.
        Используется оркестратором при входе в бой.
        """
        await self.account_manager.bulk_link_combat_session(char_ids, session_id)

    async def unlink_players_from_session(self, char_ids: list[int]) -> None:
        """
        Отвязывает игроков от боевой сессии.
        Используется при завершении боя.
        """
        await self.account_manager.bulk_unlink_combat_session(char_ids)
