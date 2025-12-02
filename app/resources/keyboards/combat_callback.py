"""
Модуль содержит определения CallbackData для взаимодействия в боевых сценах.

Определяет структуры данных для кнопок выбора зон атаки/защиты,
основных боевых действий и пагинации лога боя.
"""

from aiogram.filters.callback_data import CallbackData


class CombatZoneCallback(CallbackData, prefix="c_zone"):
    """
    Callback для кнопок выбора зон атаки/защиты.

    Attributes:
        layer: Слой действия ('atk' для атаки, 'def' для защиты).
        zone_id: Идентификатор зоны (например, 'head', 'chest', 'legs').
    """

    layer: str
    zone_id: str


class CombatActionCallback(CallbackData, prefix="c_act"):
    """
    Callback для основных боевых действий.

    Attributes:
        action: Действие (например, 'submit' для подтверждения хода, 'menu' для открытия меню).
    """

    action: str


class CombatLogCallback(CallbackData, prefix="c_log"):
    """
    Callback для пагинации лога боя.

    Attributes:
        page: Номер страницы лога для отображения.
    """

    page: int
