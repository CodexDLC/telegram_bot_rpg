# app/keyboards/inline.py
import logging
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.resources.texts.buttons_callback import Buttons


log = logging.getLogger(__name__)


def get_start_adventure_kb() -> InlineKeyboardMarkup:
    """
    Возвращает Inline-клавиатуру с кнопкой "Начать приключение".
    """
    kb = InlineKeyboardBuilder()

    for key, value in Buttons.START.items():
        kb.button(text=value, callback_data=key)

    return kb.as_markup()


def gender_kb() -> InlineKeyboardMarkup:
    """
    Возвращает Inline-клавиатуру с кнопками выбора пола.
    """
    kb = InlineKeyboardBuilder()

    for key, value in Buttons.GENDER.items():
        kb.button(text=value, callback_data=key)

    return kb.as_markup()

def confirm_kb() -> InlineKeyboardMarkup:
    """
    Возвращает Inline-клавиатуру с кнопкой подтверждения.
    """
    kb = InlineKeyboardBuilder()

    for key, value in Buttons.CONFIRM.items():
        kb.button(text=value, callback_data=key)

    return kb.as_markup()



