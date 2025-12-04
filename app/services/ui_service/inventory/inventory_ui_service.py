# app/services/ui_service/inventory/inventory_ui_service.py
from typing import Any

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from app.resources.keyboards.inventory_callback import InventoryCallback
from app.resources.schemas_dto.item_dto import EquippedSlot, InventoryItemDTO, ItemType, QuickSlot
from app.services.core_service.manager.account_manager import AccountManager
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

    def __init__(
        self,
        char_id: int,
        user_id: int,
        session: AsyncSession,
        state_data: dict[str, Any],
        account_manager: AccountManager,
    ):
        super().__init__(char_id=char_id, state_data=state_data)
        # user_id передается напрямую для генерации кнопок (security)
        self.user_id = user_id
        self.session = session
        self.inventory_service = InventoryService(
            session=self.session, char_id=self.char_id, account_manager=account_manager
        )
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

    async def render_item_list(
        self, section: str, category: str, page: int = 0, filter_type: str = "category"
    ) -> tuple[str, InlineKeyboardMarkup]:
        """
        Уровень 1: Экран списка предметов с фильтрами и пагинацией.

        Добавлен аргумент filter_type для управления рендерингом клавиатуры.
        """
        # 1. Получаем ВСЕ предметы из инвентаря (не надетые)
        all_items = await self.inventory_service.get_items("inventory")

        # 2. Фильтруем список в Python (Section -> Category/Slot)
        filtered_items = self._filter_items(
            all_items, section, category
        )  # <--- category теперь может быть именем слота

        # 3. Пагинация (Slicing)
        total_items = len(filtered_items)
        total_pages = (total_items + self.PAGE_SIZE - 1) // self.PAGE_SIZE
        if page >= total_pages and total_pages > 0:
            page = total_pages - 1

        start_idx = page * self.PAGE_SIZE
        end_idx = start_idx + self.PAGE_SIZE
        items_on_page = filtered_items[start_idx:end_idx]

        # 4. Форматируем текст
        text = self.InvF.format_item_list(
            items=items_on_page,
            section=section,
            category=category,
            page=page,
            total_pages=total_pages if total_pages > 0 else 1,
            actor_name="📦 Инвентарь",
        )

        # 5. Клавиатура: Выбор типа клавиатуры в зависимости от filter_type
        if filter_type == "slot":
            # Если пришли с Куклы, показываем только "Назад" и пагинацию
            kb = self._kb_slot_filter_list(
                section=section,
                category=category,
                page=page,
                total_pages=total_pages if total_pages > 0 else 1,
                items_on_page=items_on_page,
                filter_type=filter_type,
            )
        else:
            # Если пришли из общих категорий, показываем кнопки фильтров
            kb = self._kb_category_filter_list(
                section=section,
                category=category,
                page=page,
                total_pages=total_pages if total_pages > 0 else 1,
                items_on_page=items_on_page,
                filter_type=filter_type,
            )

        return text, kb

    def _kb_category_filter_list(
        self,
        section: str,
        category: str,
        page: int,
        total_pages: int,
        items_on_page: list[InventoryItemDTO],
        filter_type: str,
    ) -> InlineKeyboardMarkup:
        """Клавиатура для режима "Фильтр по Категории" (для ресурсов/расходников). С кнопками фильтров."""
        kb = InlineKeyboardBuilder()

        # 1. Ряд фильтров (Динамический из SUB_CATEGORIES)
        filters = self.InvF.SUB_CATEGORIES.get(section)

        if filters:
            # Добавляем кнопку "Все" (сброс фильтра)
            all_text = "✅ Все" if category == "all" else "Все"
            # ⚠️ filter_type остается "category" для этого режима
            cb_all = InventoryCallback(
                level=1, user_id=self.user_id, section=section, category="all", page=0, filter_type=filter_type
            ).pack()
            kb.button(text=all_text, callback_data=cb_all)

            # Добавляем кнопки из подкатегорий
            for f_cat, f_name in filters.items():
                btn_text = f"✅ {f_name}" if category == f_cat else f_name
                cb = InventoryCallback(
                    level=1, user_id=self.user_id, section=section, category=f_cat, page=0, filter_type=filter_type
                ).pack()
                kb.button(text=btn_text, callback_data=cb)

            kb.adjust(3)

        num_row = []
        for i, item in enumerate(items_on_page, start=(page * self.PAGE_SIZE) + 1):
            button_num = i - (page * self.PAGE_SIZE)
            # ⚠️ level=2 должен быть
            cb = InventoryCallback(
                level=2,
                user_id=self.user_id,
                section=section,
                category=category,
                page=page,
                item_id=item.inventory_id,
                filter_type=filter_type,
            ).pack()
            num_row.append(InlineKeyboardButton(text=str(button_num), callback_data=cb))

        if num_row:
            kb.row(*num_row)

        # 3. Пагинация
        nav_row = self._get_pagination_row(section, category, page, total_pages, filter_type)
        kb.row(*nav_row)

        # 4. Кнопка "Назад" (возврат на Level 0 - Кукла)
        cb_back = InventoryCallback(level=0, user_id=self.user_id).pack()
        kb.row(InlineKeyboardButton(text="↩️ Назад к Кукле", callback_data=cb_back))

        return kb.as_markup()

    def _get_pagination_row(
        self, section: str, category: str, page: int, total_pages: int, filter_type: str
    ) -> list[InlineKeyboardButton]:
        """Вспомогательный метод для создания ряда пагинации."""
        nav_row = []

        # Назад
        if page > 0:
            cb_prev = InventoryCallback(
                level=1,
                user_id=self.user_id,
                section=section,
                category=category,
                page=page - 1,
                filter_type=filter_type,
            ).pack()
            nav_row.append(InlineKeyboardButton(text="◀️", callback_data=cb_prev))
        else:
            nav_row.append(InlineKeyboardButton(text=" ", callback_data="ignore"))

        # Счетчик
        nav_row.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="ignore"))

        # Вперед
        if page < total_pages - 1:
            cb_next = InventoryCallback(
                level=1,
                user_id=self.user_id,
                section=section,
                category=category,
                page=page + 1,
                filter_type=filter_type,
            ).pack()
            nav_row.append(InlineKeyboardButton(text="▶️", callback_data=cb_next))
        else:
            nav_row.append(InlineKeyboardButton(text=" ", callback_data="ignore"))

        return nav_row

    def _kb_slot_filter_list(
        self,
        section: str,
        category: str,
        page: int,
        total_pages: int,
        items_on_page: list[InventoryItemDTO],
        filter_type: str,
    ) -> InlineKeyboardMarkup:
        """Клавиатура для режима "Фильтр по Слоту" (с Куклы). Без кнопок категорий."""
        kb = InlineKeyboardBuilder()

        # 1. Цифровая панель
        num_row = []
        for i, item in enumerate(items_on_page, start=(page * self.PAGE_SIZE) + 1):
            button_num = i - (page * self.PAGE_SIZE)
            cb = InventoryCallback(
                level=2,
                user_id=self.user_id,
                section=section,
                category=category,
                page=page,
                item_id=item.inventory_id,
                filter_type=filter_type,
            ).pack()
            num_row.append(InlineKeyboardButton(text=str(button_num), callback_data=cb))

        if num_row:
            kb.row(*num_row)

        # 2. Пагинация
        nav_row = self._get_pagination_row(section, category, page, total_pages, filter_type)
        kb.row(*nav_row)

        # 3. Кнопка "Назад" (возврат на Level 0 - Кукла)
        cb_back = InventoryCallback(level=0, user_id=self.user_id).pack()
        kb.row(InlineKeyboardButton(text="↩️ Назад к Кукле", callback_data=cb_back))

        return kb.as_markup()

    def _filter_items(self, items: list[InventoryItemDTO], section: str, category: str) -> list[InventoryItemDTO]:
        """
        Логика фильтрации списка предметов.
        """
        filtered = []

        # 1. Определение типа фильтра
        is_slot_filter = False
        try:
            EquippedSlot(category)
            is_slot_filter = True  # Это фильтр по конкретному слоту (например, head_armor)
        except ValueError:
            pass  # Это фильтр по категории продукта (например, weapon, armor)

        # Маппинг секций на типы предметов
        section_type_map = SECTION_TYPE_MAP
        allowed_types = section_type_map.get(section, [])

        for item in items:
            # 2. Фильтр по Секции (Тип предмета)
            if item.item_type not in allowed_types:
                continue

            # 3. Фильтр по Категории (Подтип/Subtype)
            if category == "all":
                filtered.append(item)
                continue

            if is_slot_filter:
                # 🔥 НОВАЯ ЛОГИКА: Фильтрация по наличию слота в valid_slots
                valid_slots = getattr(item.data, "valid_slots", [])
                if category in valid_slots:
                    filtered.append(item)
            else:
                # 🔥 СТАРАЯ ЛОГИКА: Фильтрация по названию категории продукта/группы
                if section == "resource" and item.subtype:
                    if self.inventory_service._map_subtype_to_group(item.subtype) == category:
                        filtered.append(item)
                elif item.item_type.value == category or item.subtype == category:
                    filtered.append(item)

        return filtered

    # --- KEYBOARDS ---
    def _kb_main_menu(self) -> InlineKeyboardMarkup:
        """
        Клавиатура Уровня 0: Экран Куклы.
        Каждая кнопка - это конкретный слот (Weapon, Head, Ring_1), который
        ведет к списку предметов, фильтрованных по этому слоту.
        """
        kb = InlineKeyboardBuilder()

        # Список слотов в том порядке, в котором они должны быть на клавиатуре (3 колонки)
        slot_button_order = [
            # Верхний ряд (Голова/Аксессуары)
            (EquippedSlot.HEAD_ARMOR, EquippedSlot.CHEST_GARMENT, EquippedSlot.AMULET),
            # Средний ряд (Тело/Руки)
            (EquippedSlot.CHEST_ARMOR, EquippedSlot.OUTER_GARMENT, EquippedSlot.BELT_ACCESSORY),
            # Основное Оружие/Щит
            (EquippedSlot.MAIN_HAND, EquippedSlot.OFF_HAND, EquippedSlot.TWO_HAND),
            # Нижний ряд (Ноги/Ступни)
            (EquippedSlot.LEGS_ARMOR, EquippedSlot.FEET_ARMOR, EquippedSlot.RING_1),
            # Дополнительный ряд (Аксессуары/Одежда)
            (EquippedSlot.ARMS_ARMOR, EquippedSlot.GLOVES_GARMENT, EquippedSlot.RING_2),
        ]

        # 1. Сетка слотов Куклы
        for row in slot_button_order:
            row_buttons = []
            for slot_enum in row:
                # Текст берем из Formatters, но делаем его короче
                full_name = self.InvF.SLOT_NAMES.get(slot_enum.value, slot_enum.name)

                # 🔥 КОНТРАКТ: level=1, section='equip', category=slot_enum.value
                callback_data = InventoryCallback(
                    level=1,
                    user_id=self.user_id,
                    section="equip",
                    category=str(slot_enum.value),
                    filter_type="slot",
                    page=0,
                ).pack()

                # Оставляем только иконку и короткое имя
                short_text = full_name.split()[0]

                row_buttons.append(InlineKeyboardButton(text=short_text, callback_data=callback_data))
            kb.row(*row_buttons)

        # 2. Кнопки Категорий (для ресурсов и расходников)
        kb_resources = []

        # Consumables (Расходники)
        cb_con = InventoryCallback(level=1, user_id=self.user_id, section="consumable", category="all").pack()
        kb_resources.append(InlineKeyboardButton(text=self.InvF.SECTION_NAMES["consumable"], callback_data=cb_con))

        # Resources (Руда/Ткани и т.д. - ведет на SUB-меню)
        cb_res = InventoryCallback(level=1, user_id=self.user_id, section="resource", category="all").pack()
        kb_resources.append(InlineKeyboardButton(text=self.InvF.SECTION_NAMES["resource"], callback_data=cb_res))

        kb.row(*kb_resources)

        return kb.as_markup()

    async def render_item_details(
        self, item_id: int, category: str, page: int, filter_type: str
    ) -> tuple[str, InlineKeyboardMarkup]:
        """
        Уровень 2: Карточка предмета с блоком сравнения.
        """
        item = await self.inventory_service.inventory_repo.get_item_by_id(item_id)

        if not item or item.character_id != self.char_id:
            return "❌ Предмет не найден или не принадлежит вам.", self._kb_back_to_list("all", "all", 0)

        # 1. Генерируем базовое описание (из Форматтера)
        details_text = self.InvF.format_item_details(item, actor_name="📦 Инфо")

        # 2. Генерируем Блок Сравнения (только для экипировки)
        comparison_block = ""
        if item.item_type in (ItemType.WEAPON, ItemType.ARMOR, ItemType.ACCESSORY) and item.location == "inventory":
            comparison_block = await self._generate_comparison_block(item)

        # 3. Собираем итоговый текст
        full_text = f"{details_text}\n{comparison_block}"

        # 4. Клавиатура действий
        kb = self._kb_item_details(item, category, page, filter_type)

        return full_text, kb

    async def _generate_comparison_block(self, new_item: InventoryItemDTO) -> str:
        """
        Математика сравнения: (Новое - Старое).
        Возвращает отформатированный блок текста.
        """
        if new_item.item_type in (ItemType.RESOURCE, ItemType.CURRENCY):
            return ""

        target_slots = getattr(new_item.data, "valid_slots", [])
        if not target_slots:
            return ""

        equipped_items = await self.inventory_service.get_items("equipped")

        old_item = None
        for eq in equipped_items:
            if eq.item_type in (ItemType.RESOURCE, ItemType.CURRENCY):
                continue
            eq_slots = getattr(eq.data, "valid_slots", [])
            if set(target_slots).intersection(set(eq_slots)):
                old_item = eq
                break

        if not old_item:
            return "\n⚖️ <b>Сравнение:</b>\n<i>Слот свободен. Чистая прибавка.</i>"

        diff_lines = []

        new_bonuses = new_item.data.bonuses or {}
        old_bonuses = old_item.data.bonuses or {}
        all_bonuses = set(new_bonuses.keys()) | set(old_bonuses.keys())

        for stat in all_bonuses:
            new_val = new_bonuses.get(stat, 0)
            old_val = old_bonuses.get(stat, 0)
            diff = new_val - old_val

            if diff == 0:
                continue

            sign = "+" if diff > 0 else ""
            icon = "🟢" if diff > 0 else "🔴"
            stat_name = stat.replace("_", " ").capitalize()
            diff_lines.append(f"{icon} {stat_name}: {sign}{diff}")

        if not diff_lines:
            return "\n⚖️ <b>Сравнение:</b>\n<i>Характеристики идентичны.</i>"

        return "\n⚖️ <b>Сравнение</b> (с " + old_item.data.name + "):\n<code>" + "\n".join(diff_lines) + "</code>"

    # --- КЛАВИАТУРЫ ---

    def _kb_item_details(
        self, item: InventoryItemDTO, category: str, page: int, filter_type: str
    ) -> InlineKeyboardMarkup:
        kb = InlineKeyboardBuilder()

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

        # 2. Привязка к быстрому слоту
        if item.item_type == ItemType.CONSUMABLE and item.data.is_quick_slot_compatible:
            action = "unbind_quick_slot" if item.quick_slot_position else "bind_quick_slot_menu"
            text = f"↩️ Отвязать ({item.quick_slot_position})" if item.quick_slot_position else "🔗 Привязать"

            cb_qs = InventoryCallback(
                level=3,  # НОВЫЙ УРОВЕНЬ ДЛЯ МЕНЮ ВЫБОРА
                user_id=self.user_id,
                action=action,
                item_id=item.inventory_id,
                # Передаем весь контекст обратно
                section=str(item.item_type.value),
                category=category,
                page=page,
                filter_type=filter_type,
            ).pack()
            actions_row.append(InlineKeyboardButton(text=text, callback_data=cb_qs))

        # 3. Выбросить / Распылить
        cb_drop = InventoryCallback(level=2, user_id=self.user_id, action="drop", item_id=item.inventory_id).pack()
        # Используем иконку мусорки
        actions_row.append(InlineKeyboardButton(text="🗑", callback_data=cb_drop))

        kb.row(*actions_row)

        # === Кнопка Назад ===
        # Определяем секцию на основе типа предмета
        section = "equip"  # Дефолт
        for s, types in SECTION_TYPE_MAP.items():
            if item.item_type in types:
                section = s
                break

        cb_back = InventoryCallback(
            level=1, user_id=self.user_id, section=section, category=category, page=page, filter_type=filter_type
        ).pack()

        kb.row(InlineKeyboardButton(text="🔙 Назад к списку", callback_data=cb_back))

        return kb.as_markup()

    def _kb_back_to_list(self, section: str, category: str, page: int) -> InlineKeyboardMarkup:
        """Хелпер для кнопки назад при ошибке"""
        kb = InlineKeyboardBuilder()
        cb = InventoryCallback(level=1, user_id=self.user_id, section=section, category=category, page=page).pack()
        kb.button(text="🔙 Назад", callback_data=cb)
        return kb.as_markup()

    async def render_quick_slot_selection_menu(
        self, item_id: int, context_data: dict
    ) -> tuple[str, InlineKeyboardMarkup]:
        """Рендерит сетку кнопок для выбора Quick Slot."""
        max_slots = await self.inventory_service._get_quick_slot_limit()

        # 1. Текст
        item = await self.inventory_service.inventory_repo.get_item_by_id(item_id)
        item_name = item.data.name if item else "Предмет"

        text = f"🔗 <b>Привязать {item_name}</b>\n\nВыберите свободный слот на вашем поясе (Доступно: {max_slots}):"
        kb = InlineKeyboardBuilder()

        # 2. Кнопки слотов
        for i in range(1, max_slots + 1):
            try:
                slot_enum = QuickSlot(f"quick_slot_{i}")

                # Action is 'bind_quick_slot_select'
                cb = InventoryCallback(
                    level=3,
                    user_id=self.user_id,
                    action="bind_quick_slot_select",
                    item_id=item_id,
                    category=context_data["category"],
                    page=context_data["page"],
                    filter_type=context_data["filter_type"],
                    section=slot_enum.value,  # Передаем выбранный QuickSlot
                ).pack()
                kb.button(text=str(i), callback_data=cb)
            except ValueError:
                break

        kb.adjust(4)

        # 3. Кнопка Назад (Level 2 Item Details)
        cb_back = InventoryCallback(
            level=2,
            user_id=self.user_id,
            action="view",
            item_id=item_id,
            category=context_data["category"],
            page=context_data["page"],
            filter_type=context_data["filter_type"],
        ).pack()
        kb.row(InlineKeyboardButton(text="↩️ Назад", callback_data=cb_back))

        return text, kb.as_markup()

    async def action_bind_quick_slot(self, item_id: int, quick_slot_key: str) -> tuple[bool, str]:
        """Вызывает Game Service для привязки (логика Game Service)."""
        try:
            slot_enum = QuickSlot(quick_slot_key)
            # 🔥 Вызов Game Service
            return await self.inventory_service.move_to_quick_slot(item_id, slot_enum)
        except ValueError:
            return False, "Ошибка: Неверный ключ слота."

    async def action_unbind_quick_slot(self, item_id: int) -> tuple[bool, str]:
        """Вызывает Game Service для отвязки (логика Game Service)."""
        # 🔥 Game Service должен уметь отвязывать, но здесь проще прямой вызов Repo (компромисс)
        success = await self.inventory_service.inventory_repo.update_fields(item_id, {"quick_slot_position": None})
        if success:
            return True, "↩️ Предмет отвязан."
        return False, "❌ Ошибка отвязки."
