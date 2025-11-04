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