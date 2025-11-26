# app/services/ui_service/inventory/inventory_ui_service.py
from typing import Any

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger as log

from app.resources.keyboards.inventory_callback import InventoryCallback
from app.services.game_service.inventory.inventory_service import InventoryService
from app.services.ui_service.base_service import BaseUIService
from app.services.ui_service.helpers_ui.inventory_formatters import InventoryFormatter


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
        super().__init__(char_id=char_id, state_data=state_data)
        self.user_id = state_data.get("user_id")
        self.session = state_data.get("session")
        self.inventory_service = InventoryService(session=self.session, char_id=self.char_id)
        self.InvF = InventoryFormatter()

    async def render_main_menu(self) -> tuple[str, InlineKeyboardMarkup]:
        """
        Экран 'Кукла персонажа'.
        Показывает текущую экипировку (Голова, Тело, Руки...) и кнопки основных категорий (Снаряжение, Ресурсы...).
        Данные берет через InventoryService.get_character_inventory (фильтруя equipped).
        """
        equipped = await self.inventory_service.get_items("equipped")
        current_slots, max_slots = await self.inventory_service.get_capacity()
        dust_amount = await self.inventory_service.get_dust_amount()

        text = self.InvF.format_main_menu(
            equipped=equipped, current_slots=current_slots, max_slots=max_slots, dust_amount=dust_amount
        )

        kb = self._kb_main_menu()

        return text, kb

    async def render_sub_categories(self, section: str) -> tuple[str, InlineKeyboardMarkup]:
        """
        Экран выбора подкатегории.
        Если section='equip' -> кнопки [Оружие], [Броня], [Бижутерия].
        """
        pass

    async def render_item_list(self, section: str, category: str, page: int = 0) -> tuple[str, InlineKeyboardMarkup]:
        """
        Экран списка предметов (Сетка 3x3 или список).
        1. Запрашивает предметы у InventoryService.
        2. Фильтрует их по section/category.
        3. Реализует пагинацию (срез списка).
        4. Генерирует кнопки с названиями предметов.
        """
        pass

    async def render_item_details(
        self, item_id: int, from_page: int, from_category: str
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

    def _kb_main_menu(self, level: str):
        kb = InlineKeyboardBuilder()

        section_dict = self.InvF.SECTION_NAMES.get(level)
        if not section_dict:
            log.error("")
            return None

        for key, value in section_dict:
            if level == key:
                continue
            cb = InventoryCallback(
                level=level,
                user_id=self.user_id,
            ).pack()

            kb.button(text=value, callback_data=cb)

        return kb.as_markup()
