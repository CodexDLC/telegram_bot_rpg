from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.resources.schemas_dto.character_dto import CharacterStatsReadDTO
from app.resources.texts.buttons_callback import Buttons


class OnboardingService:

    def __init__(self, user_id: int):
        self.user_id = user_id
        self.buttons = Buttons




    def get_data_start_creation_content(self):

        text = ""

        kb = self._gender_kb()


        return text , kb


    def _gender_kb(self) -> InlineKeyboardMarkup:
        """
        Возвращает Inline-клавиатуру с кнопками выбора пола.
        """
        kb = InlineKeyboardBuilder()

        for key, value in self.buttons.GENDER.items():
            kb.button(text=value, callback_data=key)

        return kb.as_markup()
