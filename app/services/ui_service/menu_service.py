# app/services/ui_service/menu_service.py
import logging
from typing import Tuple

from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardMarkup

from app.resources.keyboards.callback_data import MeinMenuCallback
from app.resources.keyboards.status_callback import StatusNavCallback
# 1. --- ДОБАВЬ ИМПОРТ StatusNavCallback ---

from app.resources.texts.menu_data.buttons_text import ButtonsTextData

log = logging.getLogger(__name__)


class MenuService:
    """
    Сервис для создания динамических верхних меню.
    ...
    """

    def __init__(self, game_stage: str, char_id: int):
        """
        Инициализирует сервис меню.
        ...
        """
        self.data = ButtonsTextData
        self.gs = game_stage
        self.char_id = char_id
        log.debug(f"Инициализирован {self.__class__.__name__} для game_stage='{self.gs}', char_id={self.char_id}")

    def get_data_menu(self) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Возвращает текст и клавиатуру для текущего меню.
        ...
        """
        log.debug("Запрос на получение данных меню.")
        text = self.data.TEXT_MENU
        kb = self._create_menu_kb()
        return text, kb

    def _create_menu_kb(self) -> InlineKeyboardMarkup:
        kb = InlineKeyboardBuilder()
        menu_layouts = self.data.MENU_LAYOUTS  #
        buttons_full_data = self.data.BUTTONS_MENU_FULL  #

        buttons_to_create = menu_layouts.get(self.gs, [])

        for key in buttons_to_create:
            button_text = buttons_full_data.get(key)

            if not button_text:
                continue

            if key == "status":
                # --- ИСПРАВЛЕНО: Просто ключ "bio" и ID ---
                callback_data = StatusNavCallback(
                    key="bio",
                    char_id=self.char_id
                ).pack()

            elif key in ("logout", "navigation", "inventory"):
                callback_data = MeinMenuCallback(
                    action=key,
                    game_stage=self.gs,
                    char_id=self.char_id
                ).pack()
            else:
                continue

            kb.button(text=button_text, callback_data=callback_data)
        log.debug(f"Клавиатура меню для game_stage='{self.gs}' успешно создана.")
        return kb.as_markup()