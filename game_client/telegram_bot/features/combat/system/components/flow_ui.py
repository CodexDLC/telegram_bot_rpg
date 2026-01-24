from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from game_client.telegram_bot.common.dto.view_dto import ViewResultDTO
from game_client.telegram_bot.common.schemas.combat import CombatDashboardDTO
from game_client.telegram_bot.features.combat.resources.formatters.combat_formatters import CombatFormatter
from game_client.telegram_bot.features.combat.resources.keyboards.combat_callback import CombatFlowCallback


class CombatFlowUI:
    """
    UI-сервис для экранов Жизненного Цикла (Flow).
    Stateless рендерер.
    """

    def __init__(self):
        self.fmt = CombatFormatter

    # render_waiting_screen УДАЛЕН (используется стандартный render_content)

    async def render_spectator_mode(self, snapshot: CombatDashboardDTO) -> ViewResultDTO:
        """Экран наблюдателя, если игрок пал."""
        # Используем стандартный форматтер, но без цели
        player_dict = snapshot.hero.model_dump()

        text = self.fmt.format_dashboard(
            player_state=player_dict,
            target_state=None,  # Нет цели
            enemies_list=[e.model_dump() for e in snapshot.enemies],
            allies_list=[a.model_dump() for a in snapshot.allies],
            timer_text="💀 <b>ВЫ МЕРТВЫ</b> | ⏳ <i>Бой продолжается...</i>",
        )

        # Клавиатура наблюдателя (Только выход или обновление)
        from game_client.telegram_bot.features.combat.resources.keyboards.combat_callback import CombatMenuCallback

        kb = InlineKeyboardBuilder()
        cb_refresh = CombatMenuCallback(action="refresh").pack()
        cb_leave = CombatFlowCallback(action="leave").pack()

        kb.row(InlineKeyboardButton(text="🔄 Обновить", callback_data=cb_refresh))
        kb.row(InlineKeyboardButton(text="🏳️ Покинуть бой", callback_data=cb_leave))

        return ViewResultDTO(text=text, kb=kb.as_markup())

    async def render_results(self, snapshot: CombatDashboardDTO) -> ViewResultDTO:
        """Экран итогов боя."""
        # TODO: Реализовать, когда будет известен формат наград
        text = "🏁 <b>Бой завершен!</b>\n\n<i>Результаты обрабатываются...</i>"

        kb = InlineKeyboardBuilder()
        cb_leave = CombatFlowCallback(action="leave").pack()
        kb.row(InlineKeyboardButton(text="🔙 Выйти в Хаб", callback_data=cb_leave))
        return ViewResultDTO(text=text, kb=kb.as_markup())
