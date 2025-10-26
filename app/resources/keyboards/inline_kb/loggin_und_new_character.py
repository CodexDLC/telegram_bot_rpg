# app/keyboards/inline.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.resources.texts.buttons_callback import START_ADVENTURE_CALLBACK, START_ADVENTURE


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