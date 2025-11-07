# app/services/ui_service/menu_service.py
import logging

from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardMarkup

from app.resources.keyboards.callback_data import MeinMenuCallback
from app.resources.texts.menu_data.buttons_text import ButtonsTextData

log = logging.getLogger(__name__)


class MenuService:
    """
    Сервис для создания динамических меню.

    Этот класс отвечает за генерацию текста и клавиатуры для "главного"
    меню, которое отображается в верхней части экрана. Содержимое меню
    (набор кнопок) зависит от текущего этапа игры (`game_stage`).
    """

    def __init__(self, game_stage: str, char_id: int):
        """
        Инициализирует сервис меню.

        Args:
            game_stage (str): Текущий этап игры (например, "creation",
                "tutorial", "world"). Определяет, какие кнопки будут в меню.
            char_id (int): ID персонажа, для которого создается меню.
                Этот ID будет "зашит" в callback-данные кнопок.
        """
        self.data = ButtonsTextData
        self.gs = game_stage
        self.char_id = char_id

    def get_data_menu(self) -> tuple[str, InlineKeyboardMarkup]:
        """
        Возвращает текст и клавиатуру для текущего меню.

        Returns:
            tuple[str, InlineKeyboardMarkup]: Кортеж, содержащий
            стандартный текст меню и сгенерированную клавиатуру.
        """
        text = self.data.TEXT_MENU
        kb = self._create_menu_kb()
        return text, kb

    def _create_menu_kb(self) -> InlineKeyboardMarkup:
        """
        Создает клавиатуру меню на основе текущего этапа игры.

        Логика работы:
        1. Определяет текущий этап игры (`self.gs`).
        2. Из `MENU_LAYOUTS` получает список ключей кнопок для этого этапа.
        3. Для каждого ключа находит текст кнопки в `BUTTONS_MENU_FULL`.
        4. Создает кнопку с соответствующим текстом и `MeinMenuCallback`,
           в который упаковываются `action`, `game_stage` и `char_id`.

        Returns:
            InlineKeyboardMarkup: Готовая клавиатура меню.
        """
        kb = InlineKeyboardBuilder()

        # Словари с данными для кнопок и раскладок
        menu_layouts = self.data.MENU_LAYOUTS
        buttons_full_data = self.data.BUTTONS_MENU_FULL

        # Получаем список кнопок, которые должны быть на данном этапе игры.
        buttons_to_create = menu_layouts.get(self.gs, [])

        for key in buttons_to_create:
            if key in buttons_full_data:
                # Создаем callback, содержащий всю необходимую информацию
                # для идентификации нажатой кнопки и контекста.
                callback_data = MeinMenuCallback(
                    action=key,
                    game_stage=self.gs,
                    char_id=self.char_id
                ).pack()

                kb.button(
                    text=f"{buttons_full_data.get(key)}",
                    callback_data=callback_data
                )

        # Здесь можно будет настроить `adjust`, если потребуется
        # расположить кнопки в несколько столбцов.
        return kb.as_markup()
