# apps/bot/resources/keyboards/inline_kb/loggin_und_new_character.py
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from apps.bot.resources.keyboards.callback_data import GenderCallback  # Новый импорт
from apps.bot.resources.texts.buttons_callback import Buttons


def get_start_adventure_kb() -> InlineKeyboardMarkup:
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
        # Используем GenderCallback
        kb.button(text=value, callback_data=GenderCallback(value=key).pack())
    return kb.as_markup()


def confirm_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for key, value in Buttons.CONFIRM.items():
        kb.button(text=value, callback_data=key)
    return kb.as_markup()
