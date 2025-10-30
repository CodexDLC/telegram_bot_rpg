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

    for key, value in Buttons.TUTORIAL_START_BUTTON.items():
        kb.button(text=value, callback_data=key)

    return kb.as_markup()


def tutorial_kb(data: dict[str, str]) -> InlineKeyboardMarkup:
    """
    Возвращает Inline-клавиатуру с кнопкой для туториал.
    """

    kb = InlineKeyboardBuilder()
    if data:
        for key, value in data.items():
            kb.button(text=value, callback_data=key)
            kb.adjust(1)

    return kb.as_markup()



# ===== Login и Инициация создания персонажа по выбору игрока, а не первого=====

def get_character_lobby_kb(
    characters: list,
    selected_char_id: int | None,
    max_slots: int = 4
) -> InlineKeyboardMarkup:

    """
        Клавиатура стартового меню лобби выбора персонажа
    """

    kb = InlineKeyboardBuilder()
    lobby_data = Buttons.LOBBY

    # === Блок персонажей (2x2) ===
    for i in range(max_slots):
        if i < len(characters):
            char = characters[i]
            kb.button(
                text=f"{'✅ ' if char.character_id == selected_char_id else '👤 '}{char.name}",
                callback_data=f"lobby:select:{char.character_id}"
            )
        else:
            kb.button(text=lobby_data["lobby:create"], callback_data="lobby:create")

    kb.adjust(2, 2)

    # === Блок действий (по одной на строку) ===
    actions = ["logout",]
    for cb in actions:
        kb.row(InlineKeyboardButton(text=lobby_data[cb], callback_data=cb))

    return kb.as_markup()

def get_character_data_bio()-> InlineKeyboardMarkup:
    """
    Клавиатура логина и показа информации о персонаже
    """

    lobby_data = Buttons.LOBBY

    kb = InlineKeyboardBuilder()

    for key, value in Buttons.LOBBY_ACTION.items():
        kb.button(text=value, callback_data=key)

    kb.adjust(2)

    actions = ["lobby:action:login",]

    for cb in actions:
        kb.row(InlineKeyboardButton(text=lobby_data[cb], callback_data=cb))

    return kb.as_markup()

