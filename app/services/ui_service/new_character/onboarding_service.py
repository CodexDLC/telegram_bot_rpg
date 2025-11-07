from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.resources.schemas_dto.character_dto import CharacterStatsReadDTO, CharacterOnboardingUpdateDTO
from app.resources.texts.buttons_callback import Buttons
from app.resources.texts.game_messages.lobby_messages import LobbyMessages
from database.repositories import get_character_repo
from database.session import get_async_session


class OnboardingService:

    def __init__(self, user_id: int, char_id : int = None):
        self.user_id = user_id
        self.buttons = Buttons
        self.new_char = LobbyMessages.NewCharacter
        if char_id:
            self.char_id = char_id
        else:
            self.char_id = None

    def get_data_start_creation_content(self):

        text =  self.new_char.GENDER_CHOICE

        kb = self._start_creation_kb()


        return text , kb


    def get_data_start_gender(self, gender_callback: str):
        """
        Возвращает текст, отображаемое имя (для UI) и значение для БД.
        """
        text = self.new_char.NAME_INPUT

        # 1. Получаем отображаемое имя (e.g. "✨ Женщина")
        gender_display = self.buttons.GENDER.get(gender_callback)

        # 2. Получаем значение для БД (e.g. "female")
        gender_db = gender_callback.split(":")[-1]

        return text, gender_display, gender_db



    def get_data_choosing_name(self):

        text = self.new_char.NAME_INPUT

        return text

    async def update_character_db(self, char_update_dto: CharacterOnboardingUpdateDTO):
        """
        Обновляет данные персонажа в БД.
        :param char_update_dto:
        :return: None
        """

        async with get_async_session() as session:
            char_repo = get_character_repo(session)
            await char_repo.update_character_onboarding(
                character_id=self.char_id,
                character_data=char_update_dto)

    def get_data_start(self, name: str, gender: str):

        text = LobbyMessages.NewCharacter.FINAL_CONFIRMATION.format(
            name=name,
            gender=gender
        )


        kb = self._tutorial_kb()

        return text, kb


    def _start_creation_kb(self) -> InlineKeyboardMarkup:
        """
        Возвращает Inline-клавиатуру с кнопками выбора пола.
        """
        kb = InlineKeyboardBuilder()

        for key, value in self.buttons.GENDER.items():
            kb.button(text=value, callback_data=key)

        return kb.as_markup()

    def _tutorial_kb(self) -> InlineKeyboardMarkup:
        """
        Возвращает Inline-клавиатуру с кнопкой для туториал.
        """
        data = self.buttons.TUTORIAL_START_BUTTON

        kb = InlineKeyboardBuilder()
        if data:
            for key, value in data.items():
                kb.button(text=value, callback_data=key)
                kb.adjust(1)

        return kb.as_markup()


