from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from apps.bot.resources.keyboards.combat_callback import CombatFlowCallback
from apps.bot.ui_service.combat.formatters.combat_formatters import CombatFormatter
from apps.bot.ui_service.helpers_ui.dto.ui_common_dto import ViewResultDTO
from apps.common.schemas_dto.combat_source_dto import CombatDashboardDTO


class CombatFlowUI:
    """
    UI-сервис для экранов Жизненного Цикла (Flow).
    Stateless рендерер.
    """

    def __init__(self):
        self.fmt = CombatFormatter

    async def render_waiting_screen(self, snapshot: CombatDashboardDTO) -> ViewResultDTO:
        """Экран ожидания просчета обмена."""
        text = (
            "<b>Ход принят.</b>\n\n"
            "⏳ <i>Ожидание ответного действия...</i>\n"
            f"<i>Целей в очереди: {snapshot.queue_count}</i>"
        )
        from apps.bot.resources.keyboards.combat_callback import CombatMenuCallback

        kb = InlineKeyboardBuilder()
        cb_refresh = CombatMenuCallback(action="refresh").pack()
        kb.row(InlineKeyboardButton(text="🔄 Обновить", callback_data=cb_refresh))
        return ViewResultDTO(text=text, kb=kb.as_markup())

    async def render_spectator_mode(self, snapshot: CombatDashboardDTO) -> ViewResultDTO:
        """Экран наблюдателя, если игрок пал."""
        enemies_text = self.fmt._format_unit_list([e.model_dump() for e in snapshot.enemies], None, is_enemy=True)
        allies_text = ""
        if snapshot.allies:
            formatted_allies = self.fmt._format_unit_list(
                [a.model_dump() for a in snapshot.allies], None, is_enemy=False
            )
            allies_text = f"\n\n<b>🔰 Союзники:</b>\n{formatted_allies}"

        text = (
            "💀 <b>ВЫ МЕРТВЫ</b>\n"
            "<i>Вы пали в бою, но ваша душа еще здесь...</i>\n\n"
            f"<b>🆚 Враги:</b>\n{enemies_text}"
            f"{allies_text}\n\n"
            "⏳ <i>Бой продолжается...</i>"
        )
        from apps.bot.resources.keyboards.combat_callback import CombatMenuCallback

        kb = InlineKeyboardBuilder()
        cb_refresh = CombatMenuCallback(action="refresh").pack()
        kb.row(InlineKeyboardButton(text="🔄 Обновить (Наблюдать)", callback_data=cb_refresh))
        return ViewResultDTO(text=text, kb=kb.as_markup())

    async def render_results(self, snapshot: CombatDashboardDTO) -> ViewResultDTO:
        """Экран итогов боя."""
        winner = snapshot.winner_team or "none"
        rewards = snapshot.rewards or {}
        text = self.fmt.format_results(
            player_snap=snapshot.player,
            winner_team=winner,
            duration=0,
            rewards=rewards,
        )
        kb = InlineKeyboardBuilder()
        cb_leave = CombatFlowCallback(action="leave").pack()
        kb.row(InlineKeyboardButton(text="🔙 Выйти в Хаб", callback_data=cb_leave))
        return ViewResultDTO(text=text, kb=kb.as_markup())
