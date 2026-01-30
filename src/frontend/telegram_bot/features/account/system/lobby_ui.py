from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.frontend.telegram_bot.base.view_dto import ViewResultDTO
from src.frontend.telegram_bot.features.account.resources.formatters.lobby_formatters import LobbyFormatter
from src.frontend.telegram_bot.features.account.resources.keyboards.account_callbacks import LobbyCallback
from src.frontend.telegram_bot.features.commands.resources.keyboards.commands_callbacks import SystemCallback
from src.shared.schemas.character import CharacterReadDTO


class LobbyUI:
    """
    UI-сервис для Lobby.
    Возвращает ViewResultDTO (text + kb).
    """

    MAX_SLOTS = 4

    def __init__(self):
        self.fmt = LobbyFormatter

    def render_lobby_menu(
        self,
        characters: list[CharacterReadDTO] | None,
        selected_char_id: int | None = None,
    ) -> ViewResultDTO:
        """
        Верхнее сообщение (menu): список персонажей + сетка + кнопки управления.
        """
        text = self.fmt.format_menu_message(characters)
        kb = self._kb_full_lobby(characters, selected_char_id)
        return ViewResultDTO(text=text, kb=kb)

    def render_delete_confirm(self, char_name: str, char_id: int) -> ViewResultDTO:
        """
        Сообщение подтверждения удаления.
        """
        text = self.fmt.format_delete_confirm(char_name)
        kb = self._kb_delete_confirm(char_id)
        return ViewResultDTO(text=text, kb=kb)

    def render_character_card(self, char: CharacterReadDTO) -> ViewResultDTO:
        """
        Нижнее сообщение (content): карточка выбранного персонажа.
        """
        text = self.fmt.format_character_card(char)
        return ViewResultDTO(text=text, kb=None)

    # --- Keyboards ---

    def _kb_full_lobby(
        self,
        characters: list[CharacterReadDTO] | None,
        selected_char_id: int | None,
    ) -> InlineKeyboardMarkup:
        """
        Полная клавиатура лобби:
        - Сетка персонажей 2x2
        - Кнопки Login/Delete (если выбран)
        - Кнопка Logout
        """
        kb = InlineKeyboardBuilder()
        chars = characters or []
        char_count = len(chars)

        # Сетка персонажей
        for i in range(self.MAX_SLOTS):
            if i < char_count:
                char = chars[i]
                is_selected = char.character_id == selected_char_id
                text = f"✅ {char.name}" if is_selected else f"👤 {char.name}"
                cb = LobbyCallback(action="select", char_id=char.character_id).pack()
            else:
                text = "➕ Создать"
                cb = LobbyCallback(action="create").pack()

            kb.button(text=text, callback_data=cb)

        kb.adjust(2, 2)

        # Кнопки управления (если персонаж выбран)
        if selected_char_id:
            kb.row(
                InlineKeyboardButton(
                    text="🚀 Войти в игру",
                    callback_data=LobbyCallback(action="login", char_id=selected_char_id).pack(),
                ),
                InlineKeyboardButton(
                    text="🗑 Удалить",
                    callback_data=LobbyCallback(action="delete", char_id=selected_char_id).pack(),
                ),
            )

        # Logout (глобальный SystemCallback)
        kb.row(
            InlineKeyboardButton(
                text="🚪 Выйти",
                callback_data=SystemCallback(action="logout").pack(),
            )
        )

        return kb.as_markup()

    def _kb_delete_confirm(self, char_id: int) -> InlineKeyboardMarkup:
        """
        Клавиатура подтверждения удаления.
        """
        kb = InlineKeyboardBuilder()

        kb.button(
            text="✅ Да, удалить",
            callback_data=LobbyCallback(action="delete_confirm", char_id=char_id).pack(),
        )
        kb.button(
            text="❌ Отмена",
            callback_data=LobbyCallback(action="delete_cancel", char_id=char_id).pack(),
        )
        kb.adjust(2)

        return kb.as_markup()
