from typing import Any

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from game_client.telegram_bot.common.dto.view_dto import ViewResultDTO
from game_client.telegram_bot.common.schemas.combat import CombatLogDTO
from game_client.telegram_bot.features.combat.resources.formatters.combat_formatters import CombatFormatter
from game_client.telegram_bot.features.combat.resources.keyboards.combat_callback import CombatMenuCallback


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
        # 1. Преобразуем DTO в список словарей
        logs_list = [entry.model_dump() for entry in log_dto.logs]

        # 2. Вычисляем total_pages
        page_size = 20  # Константа, согласованная с бэкендом
        total_pages = (log_dto.total + page_size - 1) // page_size
        if total_pages == 0:
            total_pages = 1

        # 3. Форматируем (передаем уже готовый чанк)
        text = self.fmt.format_log(logs_list, log_dto.page, total_pages)

        kb = self._kb_log_pagination(log_dto.page, total_pages)
        return ViewResultDTO(text=text, kb=kb)

    # --- Keyboards ---

    def _kb_log_pagination(self, page: int, total_pages: int) -> InlineKeyboardMarkup:
        kb = InlineKeyboardBuilder()

        prev_page = page - 1
        next_page = page + 1

        buttons = []
        if prev_page > 0:  # Страницы с 1
            buttons.append(
                InlineKeyboardButton(
                    text="⬅️", callback_data=CombatMenuCallback(action="page", value=str(prev_page)).pack()
                )
            )

        buttons.append(InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="noop"))

        if next_page <= total_pages:
            buttons.append(
                InlineKeyboardButton(
                    text="➡️", callback_data=CombatMenuCallback(action="page", value=str(next_page)).pack()
                )
            )

        kb.row(*buttons)

        cb_refresh = CombatMenuCallback(action="refresh").pack()
        kb.row(InlineKeyboardButton(text="🔄 Обновить лог", callback_data=cb_refresh))

        return kb.as_markup()
