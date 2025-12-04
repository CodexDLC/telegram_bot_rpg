"""
Модуль содержит определение CallbackData для системы инвентаря.

Предоставляет универсальную структуру данных для кнопок,
позволяющую управлять навигацией по инвентарю (уровни, секции,
категории, пагинация) и действиями с предметами.
"""

from aiogram.filters.callback_data import CallbackData


class InventoryCallback(CallbackData, prefix="inv"):
    """
    Универсальный CallbackData для системы инвентаря.

    Attributes:
        level: Уровень навигации (0=Main, 1=List, 2=ItemDetails).
        user_id: ID владельца (для защиты от нажатий другими пользователями).
        section: Основная секция инвентаря ('main', 'equip', 'resource' и т.д.).
        category: Подкатегория или фильтр ('all', 'weapon', 'ores' и т.д.).
        page: Номер страницы для пагинации.
        item_id: ID предмета (для уровня 2).
        action: Действие с предметом ('view', 'equip', 'drop' и т.д.).
    """

    level: int
    user_id: int
    section: str = "main"
    category: str = "all"
    filter_type: str = "category"
    page: int = 0
    item_id: int = 0
    action: str = "view"
