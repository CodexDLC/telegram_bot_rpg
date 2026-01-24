# app/services/ui_service/lobby_service.py

from typing import Any

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, User
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger as log

from apps.common.schemas_dto import CharacterReadDTO
from game_client.bot.resources.keyboards.callback_data import LobbySelectionCallback, SystemCallback
from game_client.bot.resources.texts.buttons_callback import Buttons
from game_client.bot.resources.texts.ui_messages import DEFAULT_ACTOR_NAME
from game_client.bot.ui_service.base_service import BaseUIService
from game_client.bot.ui_service.lobby.formatters.lobby_formatters import LobbyFormatter


class LobbyService(BaseUIService):
    """
    Сервис для управления UI-логикой лобби выбора персонажей.
    """

    def __init__(
        self,
        user: User,
        state_data: dict[str, Any],
        char_id: int | None = None,
    ):
        super().__init__(state_data=state_data, char_id=char_id or 0)
        self.user_id = user.id
        self.actor_name = DEFAULT_ACTOR_NAME
        log.debug(f"Инициализирован {self.__class__.__name__} для user_id={self.user_id}.")

    def get_message_delete(self, char_name: str) -> tuple[str, InlineKeyboardMarkup]:
        text = f"⚠️ Вы уверены, что хотите удалить персонажа <b>{char_name}</b>?\n\nЭто действие необратимо."
        kb = self._kb_delete()
        return text, kb

    def _kb_delete(self) -> InlineKeyboardMarkup:
        kb = InlineKeyboardBuilder()
        yes_b = LobbySelectionCallback(action="delete_yes", char_id=self.char_id).pack()
        no_b = LobbySelectionCallback(action="delete_no", char_id=self.char_id).pack()
        kb.button(text="Да", callback_data=yes_b)
        kb.button(text="Нет", callback_data=no_b)
        kb.adjust(2)
        return kb.as_markup()

    def get_data_lobby_start(
        self, characters: list[CharacterReadDTO] | None = None
    ) -> tuple[str, InlineKeyboardMarkup]:
        """
        Подготавливает данные для отображения стартового экрана лобби.
        """
        log.debug(f"Подготовка стартового экрана лобби для user_id={self.user_id}.")
        text = LobbyFormatter.format_character_list(characters)
        kb = self._get_character_lobby_kb(characters)
        return text, kb

    def _get_character_lobby_kb(
        self, characters: list[CharacterReadDTO] | None, max_slots: int = 4
    ) -> InlineKeyboardMarkup:
        """
        Создает клавиатуру для лобби выбора персонажа.
        """
        log.debug(f"Создание клавиатуры лобби для user_id={self.user_id}.")
        kb = InlineKeyboardBuilder()
        lobby_buttons = Buttons.LOBBY_KB_UP

        itera_char = len(characters) if characters is not None else 0

        # Создаем кнопки для существующих персонажей.
        if characters:
            for i in range(max_slots):
                if i < itera_char:
                    char = characters[i]
                    callback = LobbySelectionCallback(action="select", char_id=char.character_id)
                    text = f"✅ {char.name}" if char.character_id == self.char_id else f"👤 {char.name}"
                    kb.button(text=text, callback_data=callback.pack())
                else:
                    callback = LobbySelectionCallback(
                        action="create",
                    )
                    kb.button(text=lobby_buttons["create"], callback_data=callback.pack())
        else:
            for _ in range(max_slots):
                callback = LobbySelectionCallback(
                    action="create",
                )
                kb.button(text=lobby_buttons["create"], callback_data=callback.pack())

        kb.adjust(2, 2)

        # Добавляем кнопки управления
        buttons = self._down_button()
        for button in buttons:
            kb.row(button)

        log.debug("Клавиатура лобби успешно создана.")
        return kb.as_markup()

    def _down_button(self) -> list[InlineKeyboardButton]:
        lobby_buttons_dawn = Buttons.LOBBY_KB_DOWN
        buttons = []

        for key, value in lobby_buttons_dawn.items():
            # Если персонаж не выбран, показываем только Logout
            if (not self.char_id or self.char_id == 0) and key != "logout":
                continue

            # Если персонаж выбран, показываем всё (включая Logout)

            if key == "logout":
                callback_data = SystemCallback(action="logout").pack()
            else:
                callback_data = LobbySelectionCallback(action=key, char_id=self.char_id).pack()

            buttons.append(
                InlineKeyboardButton(
                    text=value,
                    callback_data=callback_data,
                )
            )

        return buttons
