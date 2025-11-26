# app/services/ui_service/inventory/inventory_ui_service.py
from typing import Any

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from app.resources.keyboards.inventory_callback import InventoryCallback
from app.resources.schemas_dto.item_dto import InventoryItemDTO, ItemType
from app.services.game_service.inventory.inventory_service import InventoryService
from app.services.ui_service.base_service import BaseUIService
from app.services.ui_service.helpers_ui.inventory_formatters import InventoryFormatter

SECTION_TYPE_MAP = {
    "equip": [ItemType.WEAPON, ItemType.ARMOR, ItemType.ACCESSORY],
    "resource": [ItemType.RESOURCE, ItemType.CURRENCY],
    "consumable": [ItemType.CONSUMABLE],
    # "quest": [ItemType.QUEST]
}


class InventoryUIService(BaseUIService):
    """
    Сервис для формирования UI инвентаря.
    """

    def __init__(self, char_id: int, user_id: int, session: AsyncSession, state_data: dict[str, Any]):
        super().__init__(char_id=char_id, state_data=state_data)
        # user_id передается напрямую для генерации кнопок (security)
        self.user_id = user_id
        self.session = session
        self.inventory_service = InventoryService(session=self.session, char_id=self.char_id)
        self.InvF = InventoryFormatter

        # Размер страницы (сетка 3x3 = 9 предметов)
        self.PAGE_SIZE = 9

    async def render_main_menu(self) -> tuple[str, InlineKeyboardMarkup]:
        """
        Уровень 0: Экран 'Кукла персонажа'.
        """
        equipped = await self.inventory_service.get_items("equipped")
        current_slots, max_slots = await self.inventory_service.get_capacity()
        dust_amount = await self.inventory_service.get_dust_amount()

        text = self.InvF.format_main_menu(
            equipped=equipped, current_slots=current_slots, max_slots=max_slots, dust_amount=dust_amount
        )

        kb = self._kb_main_menu()
        return text, kb

    async def render_item_list(self, section: str, category: str, page: int = 0) -> tuple[str, InlineKeyboardMarkup]:
        """
        Уровень 1: Экран списка предметов с фильтрами и пагинацией.
        """
        # 1. Получаем ВСЕ предметы из инвентаря (не надетые)
        all_items = await self.inventory_service.get_items("inventory")

        # 2. Фильтруем список в Python (Section -> Category)
        filtered_items = self._filter_items(all_items, section, category)

        # 3. Пагинация (Slicing)
        total_items = len(filtered_items)
        total_pages = (total_items + self.PAGE_SIZE - 1) // self.PAGE_SIZE
        # Защита от выхода за границы (если удалили предмет и стр. сместилась)
        if page >= total_pages and total_pages > 0:
            page = total_pages - 1

        start_idx = page * self.PAGE_SIZE
        end_idx = start_idx + self.PAGE_SIZE
        items_on_page = filtered_items[start_idx:end_idx]

        # 4. Форматируем текст
        # Передаем items_on_page, чтобы форматтер отрисовал только их
        text = self.InvF.format_item_list(
            items=items_on_page,
            section=section,
            category=category,
            page=page,
            total_pages=total_pages if total_pages > 0 else 1,
            actor_name="📦 Инвентарь",
        )

        # 5. Клавиатура
        kb = self._kb_item_list(
            section=section,
            category=category,
            page=page,
            total_pages=total_pages if total_pages > 0 else 1,
            items_on_page=items_on_page,
        )

        return text, kb

    def _filter_items(self, items: list[InventoryItemDTO], section: str, category: str) -> list[InventoryItemDTO]:
        """
        Логика фильтрации списка предметов.
        """
        filtered = []

        # Маппинг секций на типы предметов
        section_type_map = SECTION_TYPE_MAP
        allowed_types = section_type_map.get(section, [])

        # Получаем маппинг подтипов для ресурсов из InventoryService
        resource_subtype_map = InventoryService._map_subtype_to_group

        for item in items:
            # 1. Фильтр по Секции (Тип предмета)
            if item.item_type not in allowed_types:
                continue

            # 2. Фильтр по Категории (Подтип/Subtype)
            if category != "all":
                # Для ресурсов используем гибкое сравнение
                if section == "resource" and item.subtype:
                    if resource_subtype_map(self, item.subtype) != category:
                        continue
                # Для остального - точное совпадение
                elif item.item_type.value != category and item.subtype != category:
                    continue

            filtered.append(item)

        return filtered

    # --- KEYBOARDS ---

    def _kb_main_menu(self) -> InlineKeyboardMarkup:
        """
        Клавиатура уровня 0: 4 большие кнопки категорий.
        """
        kb = InlineKeyboardBuilder()

        sections = {
            "equip": self.InvF.SECTION_NAMES["equip"],
            "resource": self.InvF.SECTION_NAMES["resource"],
            "component": "⚙️ Компоненты",  # (Пока нет в ItemType, но заглушка)
            "quest": "📜 Квестовые",
        }

        for sec_key, sec_name in sections.items():
            cb = InventoryCallback(level=1, user_id=self.user_id, section=sec_key, category="all", page=0).pack()
            kb.button(text=sec_name, callback_data=cb)

        kb.adjust(2)  # Сетка 2x2
        return kb.as_markup()

    def _kb_item_list(
        self, section: str, category: str, page: int, total_pages: int, items_on_page: list[InventoryItemDTO]
    ) -> InlineKeyboardMarkup:
        """
        Клавиатура уровня 1 (Универсальная): Фильтры + Сетка + Навигация.
        """
        kb = InlineKeyboardBuilder()

        # 1. Ряд фильтров (Динамический из SUB_CATEGORIES)
        # Получаем словарь подкатегорий для текущей секции (например, equip -> {weapon:..., armor:...})
        filters = self.InvF.SUB_CATEGORIES.get(section)

        if filters:
            # Добавляем кнопку "Все" (сброс фильтра)
            all_text = "✅ Все" if category == "all" else "Все"
            cb_all = InventoryCallback(level=1, user_id=self.user_id, section=section, category="all", page=0).pack()
            kb.button(text=all_text, callback_data=cb_all)

            # Добавляем кнопки из подкатегорий
            for f_cat, f_name in filters.items():
                # Берем иконку из названия (обычно она первая) или просто Название
                # Упростим: Если активно -> ✅, иначе просто Название
                btn_text = f"✅ {f_name}" if category == f_cat else f_name

                cb = InventoryCallback(level=1, user_id=self.user_id, section=section, category=f_cat, page=0).pack()
                kb.button(text=btn_text, callback_data=cb)

            # Выравниваем: Кнопка "Все" + сколько влезет (по 3 в ряд)
            kb.adjust(3)

            # 2. Цифровая панель (1-9)
        num_row = []
        # Используем enumerate(start=1), чтобы цифры совпадали с текстом (1. Меч...)
        for i, item in enumerate(items_on_page, start=(page * self.PAGE_SIZE) + 1):
            # Вычисляем "локальный" номер для кнопки (1-9 на текущей странице)
            button_num = i - (page * self.PAGE_SIZE)

            cb = InventoryCallback(
                level=2,  # Переход к деталям
                user_id=self.user_id,
                section=section,
                category=category,
                page=page,
                item_id=item.inventory_id,
            ).pack()
            num_row.append(InlineKeyboardButton(text=str(button_num), callback_data=cb))

        if num_row:
            kb.row(*num_row)

        # 3. Пагинация
        nav_row = []
        # Назад
        if page > 0:
            cb_prev = InventoryCallback(
                level=1, user_id=self.user_id, section=section, category=category, page=page - 1
            ).pack()
            nav_row.append(InlineKeyboardButton(text="◀️", callback_data=cb_prev))
        else:
            nav_row.append(InlineKeyboardButton(text=" ", callback_data="ignore"))  # Заглушка для красоты

        # Счетчик
        nav_row.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="ignore"))

        # Вперед
        if page < total_pages - 1:
            cb_next = InventoryCallback(
                level=1, user_id=self.user_id, section=section, category=category, page=page + 1
            ).pack()
            nav_row.append(InlineKeyboardButton(text="▶️", callback_data=cb_next))
        else:
            nav_row.append(InlineKeyboardButton(text=" ", callback_data="ignore"))

        kb.row(*nav_row)

        # 4. Кнопка "Назад" (на уровень 0)
        cb_back = InventoryCallback(level=0, user_id=self.user_id).pack()
        kb.row(InlineKeyboardButton(text="↩️ Назад", callback_data=cb_back))

        return kb.as_markup()
