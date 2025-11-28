# app/resources/keyboards/combat_callback.py
from aiogram.filters.callback_data import CallbackData


class CombatZoneCallback(CallbackData, prefix="c_zone"):
    """
    Кнопки сетки (Атака / Защита).
    layer: 'atk' (Атака) или 'def' (Защита)
    zone_id: 'head', 'chest', 'legs', 'feet' и т.д.
    """

    layer: str
    zone_id: str


class CombatActionCallback(CallbackData, prefix="c_act"):
    """
    Кнопки действий (Меню, Подтверждение, Побег, Пояс).
    action: 'submit', 'menu', 'belt', 'spells', 'flee'
    """

    action: str


class CombatLogCallback(CallbackData, prefix="c_log"):
    """
    Пагинация лога.
    page: Номер страницы
    """

    page: int
