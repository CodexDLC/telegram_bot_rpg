from typing import Any

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from apps.bot.resources.keyboards.combat_callback import CombatMenuCallback
from apps.bot.ui_service.combat.formatters.combat_formatters import CombatFormatter
from apps.bot.ui_service.helpers_ui.dto.ui_common_dto import ViewResultDTO
from apps.common.schemas_dto.combat_source_dto import CombatLogDTO


class CombatMenuUI:
    """
    UI-сервис для Верхнего сообщения (Menu Message).
    Stateless рендерер.
    """

    def __init__(self):
        self.fmt = CombatFormatter

    async def render_menu(self, view_type: str, data: Any) -> ViewResultDTO:
        """
        Единая точка входа для рендера меню.
        view_type: 'log', 'info', 'settings'
        data: DTO с данными (CombatLogDTO для лога, dict для инфо и т.д.)
        """
        if view_type == "log":
            if isinstance(data, CombatLogDTO):
                return await self._render_log(data)
            else:
                return ViewResultDTO(text="Ошибка данных лога.")

        return ViewResultDTO(text="Меню не реализовано.")

    # --- Internal Renderers ---

    async def _render_log(self, log_dto: CombatLogDTO) -> ViewResultDTO:
        """Отрисовка лога боя."""
        import json

        parsed_logs = []
        for log_json in log_dto.logs:
            try:
                parsed_logs.append(json.loads(log_json))
            except json.JSONDecodeError:
                continue

        text = self.fmt.format_log(parsed_logs, log_dto.page, 5)
        kb = self._kb_log_pagination(log_dto.page, log_dto.total_pages)
        return ViewResultDTO(text=text, kb=kb)

    # --- Keyboards ---

    def _kb_log_pagination(self, page: int, total_pages: int) -> InlineKeyboardMarkup:
        kb = InlineKeyboardBuilder()

        prev_page = page - 1
        next_page = page + 1

        buttons = []
        if prev_page >= 0:
            buttons.append(
                InlineKeyboardButton(
                    text="⬅️", callback_data=CombatMenuCallback(action="page", value=str(prev_page)).pack()
                )
            )

        buttons.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="noop"))

        if next_page < total_pages:
            buttons.append(
                InlineKeyboardButton(
                    text="➡️", callback_data=CombatMenuCallback(action="page", value=str(next_page)).pack()
                )
            )

        kb.row(*buttons)

        cb_refresh = CombatMenuCallback(action="refresh").pack()
        kb.row(InlineKeyboardButton(text="🔄 Обновить лог", callback_data=cb_refresh))

        return kb.as_markup()
