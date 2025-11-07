from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, User
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.resources.schemas_dto.character_dto import CharacterReadDTO, CharacterOnboardingUpdateDTO
from app.resources.texts.buttons_callback import Buttons
from app.services.helpers_module.DTO_helper import fsm_store
from app.services.ui_service.helpers_ui.lobby_formatters import LobbyFormatter
from app.resources.schemas_dto.character_dto import CharacterShellCreateDTO
from database.repositories import get_character_repo
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


    async def get_data_lobby_start(self):

        text = LobbyFormatter.format_character_list(self.characters)

        kb = await self._get_character_lobby_kb()

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
                    text=f"{'✅ ' if char.get('character_id') == self.selected_char_id else '👤 '}{char.get('name')}",
                    callback_data=f"lobby:select:{char.get('character_id')}"
                )
            else:
                kb.button(text=lobby_data["lobby:create"], callback_data="lobby:create")

        kb.adjust(2, 2)

        # === Блок действий (по одной на строку) ===
        actions = ["logout", "lobby:login"]
        for cb in actions:
            kb.row(InlineKeyboardButton(text=lobby_data[cb], callback_data=cb))

        return kb.as_markup()


    async def create_und_get_character_id(self):

        dto_object = CharacterShellCreateDTO(
            user_id=self.user_id
        )

        async with get_async_session() as session:
            char_repo = get_character_repo(session)
            char_id = await char_repo.create_character_shell(dto_object)

        return char_id

    async def update_character_db(self, char_update_dto: CharacterOnboardingUpdateDTO):

        async with get_async_session() as session:
            char_repo = get_character_repo(session)
            await char_repo.update_character_onboarding(
                character_id=self.selected_char_id,
                character_data=char_update_dto)
