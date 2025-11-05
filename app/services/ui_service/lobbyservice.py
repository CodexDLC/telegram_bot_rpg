from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, User
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.resources.schemas_dto.character_dto import CharacterReadDTO
from app.resources.texts.buttons_callback import Buttons
from app.services.helpers_module.DTO_helper import fsm_store
from app.services.ui_service.helpers_ui.lobby_formatters import LobbyFormatter
from database.repositories import get_user_repo
from database.session import get_async_session


class LobbyService:

    def __init__(
            self,
            user: User,
            selected_char_id = None,
            characters: list[CharacterReadDTO] = None,
    ):

        self.buttons = Buttons
        self.characters = characters
        self.selected_char_id= selected_char_id
        self.user_id = user.id


    def get_data_lobby_start(self):

        text = LobbyFormatter.format_character_list(self.characters)

        kb = self._get_character_lobby_kb()

        return text , kb

    async def _get_character_lobby_kb(self,
            max_slots: int = 4
    ) -> InlineKeyboardMarkup:

        """
            Клавиатура стартового меню лобби выбора персонажа
        """

        kb = InlineKeyboardBuilder()
        lobby_data = Buttons.LOBBY



        characters = await fsm_store(self.characters)

        # === Блок персонажей (2x2) ===
        for i in range(max_slots):
            if i < len(characters):
                char = characters[i]
                kb.button(
                    text=f"{'✅ ' if char.character_id == self.selected_char_id else '👤 '}{char.name}",
                    callback_data=f"lobby:select:{char.character_id}"
                )
            else:
                kb.button(text=lobby_data["lobby:create"], callback_data="lobby:create")

        kb.adjust(2, 2)

        # === Блок действий (по одной на строку) ===
        actions = ["logout", "lobby:login"]
        for cb in actions:
            kb.row(InlineKeyboardButton(text=lobby_data[cb], callback_data=cb))

        return kb.as_markup()