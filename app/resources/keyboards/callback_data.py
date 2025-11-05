# app/resources/keyboards/callback_data.py
from sys import prefix

from aiogram.filters.callback_data import CallbackData


class StatusMenuCallback(CallbackData, prefix="sm"):
    """

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

    level: 'group' (кнопка группы) или 'detail' (кнопка навыка)
    value: 'combat_base' (название группы) или 'melee_combat' (ключ навыка)
    char_id: ID персонажа
    view_mode: 'lobby' или 'full_access'
    """
    level: str
    value: str
    char_id: int
    view_mode: str


class MeinMenuCallback(CallbackData, prefix="menu"):
    """
    action:         Какую кнопку нажали какой обработчик вызвать
    game_stage:     Сколько кнопок доступно
    char_id:        ID персонажа
    """

    action: str
    game_stage: str
    char_id: int
