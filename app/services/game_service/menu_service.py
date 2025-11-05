#
import logging

from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.resources.keyboards.callback_data import MeinMenuCallback
from app.resources.texts.menu_data.buttons_text import ButtonsTextData

log = logging.getLogger(__name__)




class MenuService:

    def __init__(self, game_stage: str, char_id: int):

        self.data = ButtonsTextData
        self.gs = game_stage
        self.char_id = char_id


    def get_data_menu(self):

        text = self.data.TEXT_MENU

        kb = self._create_menu_kb()

        return text, kb

    def _create_menu_kb(self):

        kb = InlineKeyboardBuilder()

        ml = self.data.MENU_LAYOUTS
        bmf= self.data.BUTTONS_MENU_FULL

        buttons_make = ml.get(self.gs)

        for key in buttons_make:
            if key in bmf:

                callback = MeinMenuCallback(
                    action=key,
                    game_stage=self.gs,
                    char_id=self.char_id
                ).pack()

                kb.button(text=f"{bmf.get(key)}", callback_data=callback)

        return kb.as_markup()














