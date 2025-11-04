# app/resources/keyboards/callback_data.py
from aiogram.filters.callback_data import CallbackData


class StatusMenuCallback(CallbackData, prefix="sm"):
    """
    Наш новый "Стандарт" для всех кнопок меню статуса.

    action: 'bio', 'skills'
    char_id: 1, 2, 3...
    view_mode: 'lobby', 'full_access'

    (Aiogram сам превратит это в строку: "sm:bio:123:lobby")
    """
    action: str
    char_id: int
    view_mode: str


class SkillMenuCallback(CallbackData, prefix="skm"):
    """
    Наш "второй" стандарт для МЕНЮ НАВЫКОВ.
    Отвечает за группы и детали.

    level: 'group' (кнопка группы) или 'detail' (кнопка навыка)
    value: 'combat_base' (название группы) или 'melee_combat' (ключ навыка)
    char_id: ID персонажа
    view_mode: 'lobby' или 'full_access'
    """
    level: str
    value: str
    char_id: int
    view_mode: str