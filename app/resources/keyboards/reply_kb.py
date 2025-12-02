"""
Модуль содержит определения Reply-клавиатур для взаимодействия с пользователем.

Предоставляет функции для создания стандартных Reply-клавиатур,
таких как клавиатура для восстановления после ошибок.
"""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from loguru import logger as log

RESTART_BUTTON_TEXT = "🔄 Рестарт"
SETTINGS_BUTTON_TEXT = "⚙️ Настройки"
BUG_REPORT_BUTTON_TEXT = "🐞 Сообщить об ошибке"


def get_error_recovery_kb() -> ReplyKeyboardMarkup:
    """
    Возвращает Reply-клавиатуру для восстановления после ошибки.

    Кнопки: [Рестарт], [Настройки], [Баг-репорт].

    Returns:
        Объект `ReplyKeyboardMarkup` с кнопками восстановления.
    """
    log.debug("ReplyKeyboard | action=create_error_recovery_kb")
    kb = ReplyKeyboardBuilder()

    kb.add(KeyboardButton(text=RESTART_BUTTON_TEXT))
    kb.add(KeyboardButton(text=SETTINGS_BUTTON_TEXT))
    kb.add(KeyboardButton(text=BUG_REPORT_BUTTON_TEXT))

    kb.adjust(1, 2)

    return kb.as_markup(resize_keyboard=True, input_field_placeholder="Произошла ошибка. Используйте кнопки...")
