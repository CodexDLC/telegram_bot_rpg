from aiogram.filters.callback_data import CallbackData


class InventoryCallback(CallbackData, prefix="inv"):
    """
    Универсальный колбэк для системы инвентаря v3.0.
    Позволяет навигироваться между Куклой, Списками и Деталями.
    """

    # --- Уровень навигации (level) ---
    # 'main'   - Главная (Кукла персонажа + Кнопки категорий)
    # 'sub'    - Меню выбора подкатегории (Нажал "Экипировка" -> Видишь "Оружие", "Броня"...)
    # 'list'   - Список предметов 3x3 (Конкретная категория, например "Оружие")
    # 'item'   - Детальный просмотр предмета (Карточка вещи)
    level: str

    # --- Владелец (security) ---
    # Чтобы Вася не нажимал кнопки в инвентаре Пети
    user_id: int

    # --- Фильтрация (для level='list' и 'sub') ---
    # Основная секция: 'equip', 'resource', 'component', 'quest', 'currency'
    section: str = "none"

    # Подкатегория: 'weapon', 'armor', 'dust', 'ore'... (соответствует subtype в БД)
    category: str = "none"

    # --- Навигация по списку ---
    page: int = 0

    # --- Действия с предметом (для level='item') ---
    # ID предмета в базе (inventory_id)
    item_id: int = 0

    # Действие: 'view' (просмотр), 'equip' (надеть), 'unequip' (снять), 'drop' (выбросить)
    action: str = "view"
