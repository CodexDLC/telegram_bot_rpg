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

        for item in items:
            # 1. Фильтр по Секции (Тип предмета)
            if item.item_type not in allowed_types:
                continue

            # 2. Фильтр по Категории (Подтип/Subtype)
            if category != "all":
                # Для ресурсов используем гибкое сравнение
                if section == "resource" and item.subtype:
                    if self.inventory_service._map_subtype_to_group(item.subtype) != category:
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
            # "component": self.InvF.SECTION_NAMES["component"],
            # "quest": self.InvF.SECTION_NAMES["quest"],
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

    async def render_item_details(self, item_id: int) -> tuple[str, InlineKeyboardMarkup]:
        """
        Уровень 2: Карточка предмета с блоком сравнения.
        """
        item = await self.inventory_service.inventory_repo.get_item_by_id(item_id)

        if not item or item.character_id != self.char_id:
            return "❌ Предмет не найден или не принадлежит вам.", self._kb_back_to_list("all", "all", 0)

        # 1. Генерируем базовое описание (из Форматтера)
        # Используем "System" как заглушку, или self.actor_name, если он есть в BaseUIService
        details_text = self.InvF.format_item_details(item, actor_name="📦 Инфо")

        # 2. Генерируем Блок Сравнения (только для экипировки)
        comparison_block = ""
        if item.item_type in (ItemType.WEAPON, ItemType.ARMOR, ItemType.ACCESSORY) and item.location == "inventory":
            comparison_block = await self._generate_comparison_block(item)

        # 3. Собираем итоговый текст
        full_text = f"{details_text}\n{comparison_block}"

        # 4. Клавиатура действий
        kb = self._kb_item_details(item, self.state_data)

        return full_text, kb

    async def _generate_comparison_block(self, new_item: InventoryItemDTO) -> str:
        """
        Математика сравнения: (Новое - Старое).
        Возвращает отформатированный блок текста.
        """
        # 1. Ищем, что сейчас надето в эти слоты
        # Берем первый валидный слот для простоты сравнения (обычно chest, head и т.д. однозначны)
        # Для колец/оружия сложнее, но для MVP берем "первое попавшееся" в этом слоте
        target_slots = getattr(new_item.data, "valid_slots", [])
        if not target_slots:
            return ""

        equipped_items = await self.inventory_service.get_items("equipped")

        # Ищем конкурента (предмет, занимающий тот же слот)
        old_item = None
        for eq in equipped_items:
            # Проверяем пересечение слотов (если хоть один совпал - это конкурент)
            eq_slots = getattr(eq.data, "valid_slots", [])
            if set(target_slots).intersection(set(eq_slots)):
                old_item = eq
                break

                # Если сравнивать не с чем - не показываем блок (или пишем "Слот пуст")
        if not old_item:
            return "\n⚖️ <b>Сравнение:</b>\n<i>Слот свободен. Чистая прибавка.</i>"

        # 2. Считаем разницу бонусов
        diff_lines = []

        # Объединяем ключи бонусов (могут быть разные статы)
        all_bonuses = set(new_item.data.bonuses.keys()) | set(old_item.data.bonuses.keys())

        # Добавляем базовые статы (Урон / Защита)
        # Для простоты пока берем только bonuses из JSON,
        # но в будущем сюда надо добавить damage_min/max и protection

        for stat in all_bonuses:
            new_val = new_item.data.bonuses.get(stat, 0)
            old_val = old_item.data.bonuses.get(stat, 0)
            diff = new_val - old_val

            if diff == 0:
                continue

            # Форматирование строки
            sign = "+" if diff > 0 else ""
            icon = "🟢" if diff > 0 else "🔴"

            # Перевод названий статов (в идеале брать из словаря)
            stat_name = stat.replace("_", " ").capitalize()

            diff_lines.append(f"{icon} {stat_name}: {sign}{diff}")

        if not diff_lines:
            return "\n⚖️ <b>Сравнение:</b>\n<i>Характеристики идентичны.</i>"

        return "\n⚖️ <b>Сравнение</b> (с " + old_item.data.name + "):\n<code>" + "\n".join(diff_lines) + "</code>"

    # --- КЛАВИАТУРЫ ---

    def _kb_item_details(self, item: InventoryItemDTO, state_data: dict) -> InlineKeyboardMarkup:
        kb = InlineKeyboardBuilder()

        # Получаем контекст для кнопки "Назад" (откуда мы пришли?)
        # Если мы пришли из списка, state должен помнить section/category/page.
        # Если нет - ставим дефолт.
        # (Пока упростим и вернем просто в список той же категории)

        # Для простоты возврата используем item_type как категорию фильтра (грубо, но сработает для MVP)

        # === Кнопки Действий ===
        actions_row = []

        # 1. Надеть / Снять
        if item.location == "equipped":
            cb_unequip = InventoryCallback(
                level=2, user_id=self.user_id, action="unequip", item_id=item.inventory_id
            ).pack()
            actions_row.append(InlineKeyboardButton(text="🔻 Снять", callback_data=cb_unequip))

        elif item.location == "inventory":
            # Проверяем, можно ли надеть (тип)
            if item.item_type in (ItemType.WEAPON, ItemType.ARMOR, ItemType.ACCESSORY):
                cb_equip = InventoryCallback(
                    level=2, user_id=self.user_id, action="equip", item_id=item.inventory_id
                ).pack()
                actions_row.append(InlineKeyboardButton(text="✅ Надеть", callback_data=cb_equip))

        # 2. Выбросить / Распылить
        cb_drop = InventoryCallback(level=2, user_id=self.user_id, action="drop", item_id=item.inventory_id).pack()
        # Используем иконку мусорки
        actions_row.append(InlineKeyboardButton(text="🗑", callback_data=cb_drop))

        kb.row(*actions_row)

        # === Кнопка Назад ===
        # Возвращаемся на Level 1 (Список)
        # Для точного возврата надо бы хранить page в state, но пока вернем на 0
        cb_back = InventoryCallback(
            level=1,
            user_id=self.user_id,
            section="equip",  # Тут лучше брать из state, но пока хардкод для MVP
            category="all",
            page=0,
        ).pack()

        kb.row(InlineKeyboardButton(text="🔙 Назад к списку", callback_data=cb_back))

        return kb.as_markup()

    def _kb_back_to_list(self, section: str, category: str, page: int) -> InlineKeyboardMarkup:
        """Хелпер для кнопки назад при ошибке"""
        kb = InlineKeyboardBuilder()
        cb = InventoryCallback(level=1, user_id=self.user_id, section=section, category=category, page=page).pack()
        kb.button(text="🔙 Назад", callback_data=cb)
        return kb.as_markup()
