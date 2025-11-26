from aiogram.filters.callback_data import CallbackData


class InventoryCallback(CallbackData, prefix="inv"):
    """
    Универсальный колбэк для системы инвентаря v3.0.
    Позволяет навигироваться между Куклой, Списками и Деталями.
    """

    # Основная секция: 'pyppet', 'equip', 'resource', 'component', 'quest',
    level: str
    # --- Владелец (security) ---
    # Чтобы Вася не нажимал кнопки в инвентаре Пети
    user_id: int

    # Подкатегория: 'weapon', 'armor', 'dust', 'ore'... (соответствует subtype в БД)
    category: str = "none"
    # --- Действия с предметом (для level='item') ---
    # ID предмета в базе (inventory_id)
    item_id: int = 0

    # Действие: 'view' (просмотр), 'equip' (надеть), 'unequip' (снять), 'drop' (выбросить)
    action: str = "view"
