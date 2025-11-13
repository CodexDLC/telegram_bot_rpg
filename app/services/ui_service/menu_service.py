# app/services/ui_service/menu_service.py
import logging
from typing import Tuple

from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardMarkup

# 1. --- ДОБАВЬ ИМПОРТ StatusNavCallback ---
from app.resources.keyboards.callback_data import MeinMenuCallback, StatusNavCallback
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
        """
        Создает клавиатуру меню на основе текущего этапа игры.

        1. Определяет `game_stage`.
        2. Из `MENU_LAYOUTS` получает список ключей кнопок для этого этапа.
        3. Для каждого ключа находит текст и создает кнопку с *соответствующим*
           CallbackData (`StatusNavCallback` для "status", `MeinMenuCallback`
           для всего остального).

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

            if not button_text:
                log.warning(f"Для ключа кнопки '{key}' не найден текст в BUTTONS_MENU_FULL.")
                continue


            if key == "status":

                callback_data = StatusNavCallback(
                    char_id=self.char_id,
                    level=0,
                    key="bio"  # Вход по умолчанию в "Био"
                ).pack()

            elif key in ("logout", "navigation", "inventory"):

                callback_data = MeinMenuCallback(
                    action=key,
                    game_stage=self.gs,
                    char_id=self.char_id
                ).pack()

            else:
                # Защита на случай, если мы добавим новый ключ
                # в buttons_text.py, но забудем обработать его здесь.
                log.error(
                    f"Необработанный ключ '{key}' в MenuService._create_menu_kb. "
                    f"Не удалось определить тип CallbackData."
                )
                continue

            # Добавляем кнопку с правильным callback_data
            kb.button(
                text=button_text,
                callback_data=callback_data
            )

        # Здесь можно будет настроить `adjust`, если потребуется.
        # Например, `kb.adjust(2, 1)` если кнопок 3 (статус, навигация, выйти)
        log.debug(f"Клавиатура меню для game_stage='{self.gs}' успешно создана.")
        return kb.as_markup()