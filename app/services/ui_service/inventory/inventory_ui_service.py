# app/services/ui_service/inventory/inventory_ui_service.py
from typing import Any

from aiogram.types import InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ui_service.base_service import BaseUIService


class InventoryUIService(BaseUIService):
    """
    Сервис для формирования UI инвентаря.
    Строит сообщения (текст) и клавиатуры (markup) для разных экранов:
    - Главная (Кукла)
    - Категории
    - Список предметов
    - Детали предмета
    """

    def __init__(self, state_data: dict[str, Any], char_id: int):
        """
        Инициализация базового UI сервиса.
        """
        pass

    async def render_main_menu(self, session: AsyncSession) -> tuple[str, InlineKeyboardMarkup]:
        """
        Экран 'Кукла персонажа'.
        Показывает текущую экипировку (Голова, Тело, Руки...) и кнопки основных категорий (Снаряжение, Ресурсы...).
        Данные берет через InventoryService.get_character_inventory (фильтруя equipped).
        """
        pass

    async def render_sub_categories(self, section: str) -> tuple[str, InlineKeyboardMarkup]:
        """
        Экран выбора подкатегории.
        Если section='equip' -> кнопки [Оружие], [Броня], [Бижутерия].
        """
        pass

    async def render_item_list(
        self, session: AsyncSession, section: str, category: str, page: int = 0
    ) -> tuple[str, InlineKeyboardMarkup]:
        """
        Экран списка предметов (Сетка 3x3 или список).
        1. Запрашивает предметы у InventoryService.
        2. Фильтрует их по section/category.
        3. Реализует пагинацию (срез списка).
        4. Генерирует кнопки с названиями предметов.
        """
        pass

    async def render_item_details(
        self, session: AsyncSession, item_id: int, from_page: int, from_category: str
    ) -> tuple[str, InlineKeyboardMarkup]:
        """
        Карточка предмета.
        Показывает статы, описание, редкость.
        Кнопки действий зависят от состояния предмета:
        - Если надет -> [Снять]
        - Если в сумке и type=equip -> [Надеть]
        - Всегда -> [Выбросить], [Назад]
        """
        pass
