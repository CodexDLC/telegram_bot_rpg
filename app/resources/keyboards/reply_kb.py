# app/resources/keyboards/reply_kb.py
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from loguru import logger as log

# Кнопки будут использовать эти тексты
RESTART_BUTTON_TEXT = "🔄 Рестарт"
SETTINGS_BUTTON_TEXT = "⚙️ Настройки"
BUG_REPORT_BUTTON_TEXT = "🐞 Сообщить об ошибке"


def get_error_recovery_kb() -> ReplyKeyboardMarkup:
    """
    Возвращает Reply-клавиатуру для восстановления после ошибки.
    Кнопки: [Рестарт], [Настройки], [Баг-репорт].
    """
    log.debug("Создание Reply-клавиатуры для восстановления после ошибки.")
    kb = ReplyKeyboardBuilder()

    kb.add(KeyboardButton(text=RESTART_BUTTON_TEXT))
    kb.add(KeyboardButton(text=SETTINGS_BUTTON_TEXT))
    kb.add(KeyboardButton(text=BUG_REPORT_BUTTON_TEXT))

    # Сетка 1x2 (Рестарт сверху, Настройки и Баг-репорт снизу)
    kb.adjust(1, 2)

    return kb.as_markup(resize_keyboard=True, input_field_placeholder="Произошла ошибка. Используйте кнопки...")
