#
import logging

from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.resources.texts.buttons_callback import GameStage
from app.resources.texts.menu_data.buttons_text import ButtonsTextData

log = logging.getLogger(__name__)

class MenuService:

    def __init__(self, game_stage: str):

        self.data = ButtonsTextData
        self.gs = game_stage
        self.gsd = [stage.value for stage in GameStage]


    def create_menu_kb(self):

        kb = InlineKeyboardBuilder()

        for key, value in self.data.BUTTONS_MENU_FULL.items():

            if self.gs in


