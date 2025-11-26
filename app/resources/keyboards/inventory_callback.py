# app/resources/keyboards/inventory_callback.py
from aiogram.filters.callback_data import CallbackData


class InventoryCallback(CallbackData, prefix="inv"):
    """
    Универсальный колбэк для системы инвентаря v3.0.
    """

    # level: 0=Main(Кукла), 1=List(Список), 2=Item(Детали)
    level: int

    # ID владельца (для защиты от нажатий другими юзерами)
    user_id: int

    # Основная секция: 'main', 'equip', 'resource', 'component', 'quest'
    section: str = "main"

    # Подкатегория (фильтр): 'all', 'weapon', 'armor', 'ores'...
    # Соответствует ключам в SUB_CATEGORIES или subtype предмета
    category: str = "all"

    # Пагинация (для level=1)
    page: int = 0

    # ID предмета (для level=2)
    item_id: int = 0

    # Действие (для level=2): 'view', 'equip', 'drop'
    action: str = "view"
