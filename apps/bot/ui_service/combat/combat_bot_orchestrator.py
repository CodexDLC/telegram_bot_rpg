# apps/bot/ui_service/combat/combat_bot_orchestrator.py
from aiogram.types import InlineKeyboardMarkup

from apps.bot.core_client.combat_rbc_client import CombatRBCClient
from apps.bot.ui_service.combat.combat_ui_service import CombatUIService
from apps.common.schemas_dto.combat_source_dto import CombatDashboardDTO, CombatMoveDTO

# Определяем новый тип для возвращаемых данных, чтобы было понятнее
ViewResult = tuple[str, InlineKeyboardMarkup]
FullViewResult = tuple[ViewResult, ViewResult]


class CombatBotOrchestrator:
    def __init__(self, client: CombatRBCClient, ui: CombatUIService):
        self.client = client
        self.ui = ui

    async def get_dashboard_view(self, session_id: str, char_id: int, selection: dict) -> FullViewResult:
        """
        Точка входа для Refresh и первого отображения.
        Возвращает данные для ДВУХ сообщений: контент и ЛОГ БОЯ.
        """
        snapshot = await self.client.get_snapshot(session_id, char_id)
        content_view = await self._render_by_status(snapshot, selection)
        # Второе сообщение в бою — это всегда лог (страница 0 при обновлении)
        log_view = await self.ui.render_combat_log(snapshot, page=0)
        return content_view, log_view

    async def handle_submit(self, session_id: str, char_id: int, move: CombatMoveDTO) -> FullViewResult:
        """
        Логика подтверждения хода.
        Возвращает данные для ДВУХ сообщений: контент и ЛОГ БОЯ.
        """
        new_snapshot = await self.client.register_move(session_id, char_id, move.target_id, move.model_dump())
        content_view = await self._render_by_status(new_snapshot, selection={})
        # После хода обновляем лог (страница 0)
        log_view = await self.ui.render_combat_log(new_snapshot, page=0)
        return content_view, log_view

    async def get_menu_view(self, session_id: str, char_id: int, menu_type: str) -> tuple[str, InlineKeyboardMarkup]:
        """Отрисовка подменю (скиллы/вещи). Это для одного сообщения."""
        snapshot = await self.client.get_snapshot(session_id, char_id)
        if menu_type == "skills":
            return await self.ui.render_skills_menu(snapshot)
        return await self.ui.render_items_menu(snapshot)

    async def get_log_view(self, session_id: str, char_id: int, page: int) -> tuple[str, InlineKeyboardMarkup]:
        """Отрисовка лога боя. Это для одного сообщения."""
        snapshot = await self.client.get_snapshot(session_id, char_id)
        return await self.ui.render_combat_log(snapshot, page)

    async def start_new_battle(self, players: list[int], enemies: list[int]) -> tuple[str, str, InlineKeyboardMarkup]:
        """Начинает новый бой и возвращает начальный дашборд."""
        snapshot = await self.client.start_battle(players, enemies)
        text, kb = await self._render_by_status(snapshot, {})
        return snapshot.session_id, text, kb

    async def _render_by_status(self, snapshot: CombatDashboardDTO, selection: dict) -> ViewResult:
        """
        Внутренний 'решала'. Определяет какой экран показать на основе статуса из Ядра.
        Возвращает данные для ОДНОГО сообщения (контента).
        """
        if snapshot.status == "finished":
            return await self.ui.render_results(snapshot)
        if snapshot.player.hp_current <= 0:
            return await self.ui.render_spectator_mode(snapshot)
        if snapshot.status == "waiting":
            return await self.ui.render_waiting_screen(snapshot)
        return await self.ui.render_dashboard(snapshot, selection)
