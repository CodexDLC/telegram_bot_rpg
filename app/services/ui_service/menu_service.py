# app/services/ui_service/menu_service.py

from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardMarkup
from loguru import logger as log

from app.resources.keyboards.callback_data import LobbySelectionCallback, MeinMenuCallback
from app.resources.keyboards.status_callback import StatusNavCallback
from app.resources.texts.menu_data.buttons_text import ButtonsTextData
from app.services.helpers_module.dto_helper import FSM_CONTEXT_KEY


class MenuService:
    """
    Сервис для создания динамических верхних меню.
    ...
    """

    def __init__(self, game_stage: str, state_data: dict):
        """
        Инициализирует сервис меню.
        ...
        """
        self.data = ButtonsTextData
        self.gs = game_stage
        self.state_data = state_data
        session_context = self.state_data.get(FSM_CONTEXT_KEY, {})
        self.char_id = session_context.get("char_id")
        log.debug(f"Инициализирован {self.__class__.__name__} для game_stage='{self.gs}', char_id={self.char_id}")

    def get_data_menu(self) -> tuple[str, InlineKeyboardMarkup]:
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
        menu_layouts = self.data.MENU_LAYOUTS
        buttons_full_data = self.data.BUTTONS_MENU_FULL

        buttons_to_create = menu_layouts.get(self.gs, [])

        for key in buttons_to_create:
            button_text = buttons_full_data.get(key)

            if not button_text:
                continue

            if key == "status":
                callback_data = StatusNavCallback(key="bio", char_id=self.char_id).pack()

            elif key == "logout":
                callback_data = LobbySelectionCallback(action=key).pack()

            elif key in ("navigation", "inventory"):
                callback_data = MeinMenuCallback(action=key, game_stage=self.gs, char_id=self.char_id).pack()

            elif key == "arena_test":
                # Используем тот же MeinMenuCallback, но с action='arena_start'
                callback_data = MeinMenuCallback(action="arena_start", game_stage=self.gs, char_id=self.char_id).pack()

            else:
                continue

            kb.button(text=button_text, callback_data=callback_data)
        log.debug(f"Клавиатура меню для game_stage='{self.gs}' успешно создана.")
        return kb.as_markup()
