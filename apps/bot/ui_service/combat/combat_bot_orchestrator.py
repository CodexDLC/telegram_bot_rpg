# apps/bot/ui_service/combat/combat_bot_orchestrator.py
from aiogram.types import InlineKeyboardMarkup

from apps.bot.core_client.combat_rbc_client import CombatRBCClient
from apps.bot.ui_service.combat.combat_ui_service import CombatUIService
from apps.common.schemas_dto.combat_source_dto import CombatDashboardDTO, CombatMoveDTO


class CombatBotOrchestrator:
    def __init__(self, client: CombatRBCClient, ui: CombatUIService):
        self.client = client
        self.ui = ui

    async def get_dashboard_view(
        self, session_id: str, char_id: int, selection: dict
    ) -> tuple[str, InlineKeyboardMarkup]:
        """
        Точка входа для Refresh и первого отображения.
        Один запрос в ядро — один рендер.
        """
        snapshot = await self.client.get_snapshot(session_id, char_id)
        return await self._render_by_status(snapshot, selection)

    async def handle_submit(
        self, session_id: str, char_id: int, move: CombatMoveDTO
    ) -> tuple[str, InlineKeyboardMarkup]:
        """
        Логика подтверждения хода.
        Ядро возвращает Snapshot сразу после обработки LPOP, экономим один запрос.
        """
        # register_move теперь возвращает CombatDashboardDTO
        new_snapshot = await self.client.register_move(session_id, char_id, move.target_id, move.model_dump())

        # После удара сбрасываем выделение зон (selection={})
        return await self._render_by_status(new_snapshot, selection={})

    async def get_menu_view(self, session_id: str, char_id: int, menu_type: str) -> tuple[str, InlineKeyboardMarkup]:
        """Отрисовка подменю (скиллы/вещи) без лишней логики переходов."""
        snapshot = await self.client.get_snapshot(session_id, char_id)

        if menu_type == "skills":
            return await self.ui.render_skills_menu(snapshot)
        return await self.ui.render_items_menu(snapshot)

    async def get_log_view(self, session_id: str, char_id: int, page: int) -> tuple[str, InlineKeyboardMarkup]:
        """Отрисовка лога боя."""
        snapshot = await self.client.get_snapshot(session_id, char_id)
        return await self.ui.render_combat_log(snapshot, page)

    async def start_new_battle(self, players: list[int], enemies: list[int]) -> tuple[str, str, InlineKeyboardMarkup]:
        """Начинает новый бой и возвращает начальный дашборд."""
        snapshot = await self.client.start_battle(players, enemies)
        text, kb = await self._render_by_status(snapshot, {})
        return snapshot.session_id, text, kb

    async def _render_by_status(
        self, snapshot: CombatDashboardDTO, selection: dict
    ) -> tuple[str, InlineKeyboardMarkup]:
        """
        Внутренний 'решала'. Определяет какой экран показать на основе статуса из Ядра.
        """
        if snapshot.status == "finished":
            return await self.ui.render_results(snapshot)

        if snapshot.player.hp_current <= 0:
            return await self.ui.render_spectator_mode(snapshot)

        if snapshot.status == "waiting":
            return await self.ui.render_waiting_screen(snapshot)

        # По умолчанию — боевой дашборд
        return await self.ui.render_dashboard(snapshot, selection)
