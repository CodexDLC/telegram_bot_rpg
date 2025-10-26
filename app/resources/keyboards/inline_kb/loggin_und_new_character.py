# app/keyboards/inline.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.resources.texts.buttons_callback import (
    START_ADVENTURE_CALLBACK, START_ADVENTURE,
    GENDER_MALE_TEXT, GENDER_FEMALE_TEXT

)


def get_start_adventure_kb() -> InlineKeyboardMarkup:
    """
    Возвращает Inline-клавиатуру с кнопкой "Начать приключение".
    """
    button = InlineKeyboardButton(
        text=START_ADVENTURE,
        callback_data=START_ADVENTURE_CALLBACK
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[[button]])
    return keyboard


def gender_kb() -> InlineKeyboardMarkup:
    """
    Возвращает Inline-клавиатуру с кнопками выбора пола.
    """
    kb = InlineKeyboardBuilder()

    kb.button(text=GENDER_MALE_TEXT, callback_data="gender:male")
    kb.button(text=GENDER_FEMALE_TEXT, callback_data="gender:female")

    return kb.as_markup()

def confirm_kb(gender: str) -> InlineKeyboardMarkup:
    """
    Возвращает Inline-клавиатуру с кнопкой подтверждения.
    """
    kb = InlineKeyboardBuilder()
    if gender == "male":
        kb.button(text="Я готов", callback_data="confirm")
    else:
        kb.button(text="Я готова", callback_data="confirm")

    return kb.as_markup()