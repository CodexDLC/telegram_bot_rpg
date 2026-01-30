# frontend/telegram_bot/features/exploration/system/components/list_ui.py

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.frontend.telegram_bot.base.view_dto import ViewResultDTO
from src.frontend.telegram_bot.features.exploration.resources.keyboards.exploration_callbacks import (
    ExplorationListCallback,
    NavigationCallback,
)
from src.shared.schemas.exploration import ExplorationListDTO


class ListUI:
    """
    UI-компонент для рендеринга списков (бои, игроки, и т.д.).
    Форматирует текст и строит клавиатуру на основе ExplorationListDTO.
    """

    def render(self, dto: ExplorationListDTO) -> ViewResultDTO:
        """Рендерит список с пагинацией."""
        text = self._format_text(dto)
        kb = self._build_keyboard(dto)
        return ViewResultDTO(text=text, kb=kb)

    # =========================================================================
    # Text Formatting
    # =========================================================================

    def _format_text(self, dto: ExplorationListDTO) -> str:
        """Форматирует текст списка."""
        lines = [f"<b>{dto.title}</b>", ""]

        if not dto.items:
            lines.append("<i>Список пуст.</i>")
        else:
            for i, item in enumerate(dto.items, 1):
                lines.append(f"{i}. {item.text}")

        # Pagination info
        if dto.total_pages > 1:
            lines.append("")
            lines.append(f"<code>[ Страница {dto.page}/{dto.total_pages} ]</code>")

        return "\n".join(lines)

    # =========================================================================
    # Keyboard Building
    # =========================================================================

    def _build_keyboard(self, dto: ExplorationListDTO) -> InlineKeyboardMarkup:
        """Строит клавиатуру со списком и пагинацией."""
        builder = InlineKeyboardBuilder()

        # Item buttons (1, 2, 3...)
        item_buttons = []
        for i, item in enumerate(dto.items, 1):
            callback = ExplorationListCallback(action="select", item_id=item.id).pack()
            item_buttons.append(InlineKeyboardButton(text=str(i), callback_data=callback))

        # Располагаем по 5 в ряд
        for i in range(0, len(item_buttons), 5):
            builder.row(*item_buttons[i : i + 5])

        # Navigation row: [<] [Back] [>]
        nav_row = []

        if dto.page > 1:
            prev_callback = ExplorationListCallback(action="page", page=dto.page - 1).pack()
            nav_row.append(InlineKeyboardButton(text="⬅️", callback_data=prev_callback))

        # Back button
        back_callback = self._parse_back_action(dto.back_action)
        nav_row.append(InlineKeyboardButton(text="🔙 Назад", callback_data=back_callback))

        if dto.page < dto.total_pages:
            next_callback = ExplorationListCallback(action="page", page=dto.page + 1).pack()
            nav_row.append(InlineKeyboardButton(text="➡️", callback_data=next_callback))

        builder.row(*nav_row)

        return builder.as_markup()

    def _parse_back_action(self, action: str) -> str:
        """Парсит back_action и возвращает callback_data."""
        if action == "look_around":
            return NavigationCallback(action="look_around").pack()
        # Default fallback
        return NavigationCallback(action="look_around").pack()
