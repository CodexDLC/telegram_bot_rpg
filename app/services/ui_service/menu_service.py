# app/services/ui_service/menu_service.py
import logging
from typing import Tuple

from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardMarkup

from app.resources.keyboards.callback_data import MeinMenuCallback
from app.resources.texts.menu_data.buttons_text import ButtonsTextData

log = logging.getLogger(__name__)


class MenuService:
    """
    Сервис для создания динамических верхних меню.

    Генерирует текст и клавиатуру для "главного" меню, которое
    отображается в верхней части экрана. Набор кнопок в меню зависит
    от текущего этапа игры (`game_stage`).
    """

    def __init__(self, game_stage: str, char_id: int):
        """
        Инициализирует сервис меню.

        Args:
            game_stage (str): Текущий этап игры (e.g., "creation", "lobby").
            char_id (int): ID персонажа, для которого создается меню.
                           Этот ID "зашивается" в callback-данные кнопок.
        """
        self.data = ButtonsTextData
        self.gs = game_stage
        self.char_id = char_id
        log.debug(f"Инициализирован {self.__class__.__name__} для game_stage='{self.gs}', char_id={self.char_id}")

    def get_data_menu(self) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Возвращает текст и клавиатуру для текущего меню.

        Returns:
            Tuple[str, InlineKeyboardMarkup]: Кортеж с текстом и клавиатурой.
        """
        log.debug("Запрос на получение данных меню.")
        text = self.data.TEXT_MENU
        kb = self._create_menu_kb()
        return text, kb

    def _create_menu_kb(self) -> InlineKeyboardMarkup:
        """
        Создает клавиатуру меню на основе текущего этапа игры.

        1. Определяет `game_stage`.
        2. Из `MENU_LAYOUTS` получает список ключей кнопок для этого этапа.
        3. Для каждого ключа находит текст и создает кнопку с `MeinMenuCallback`.

        Returns:
            InlineKeyboardMarkup: Готовая клавиатура меню.
        """
        kb = InlineKeyboardBuilder()
        menu_layouts = self.data.MENU_LAYOUTS
        buttons_full_data = self.data.BUTTONS_MENU_FULL

        # Получаем список ключей кнопок для текущего этапа игры.
        buttons_to_create = menu_layouts.get(self.gs, [])
        log.debug(f"Для game_stage='{self.gs}' будут созданы кнопки: {buttons_to_create}")

        if not buttons_to_create:
            log.warning(f"Для game_stage='{self.gs}' не найдено раскладки в MENU_LAYOUTS.")

        for key in buttons_to_create:
            button_text = buttons_full_data.get(key)
            if button_text:
                # Создаем callback, содержащий всю необходимую информацию.
                callback_data = MeinMenuCallback(
                    action=key,
                    game_stage=self.gs,
                    char_id=self.char_id
                ).pack()

                kb.button(
                    text=button_text,
                    callback_data=callback_data
                )
            else:
                log.warning(f"Для ключа кнопки '{key}' не найден текст в BUTTONS_MENU_FULL.")

        # Здесь можно будет настроить `adjust`, если потребуется.
        log.debug(f"Клавиатура меню для game_stage='{self.gs}' успешно создана.")
        return kb.as_markup()
