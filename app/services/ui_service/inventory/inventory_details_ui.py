# app/services/ui_service/inventory/inventory_details_ui.py
from typing import Any

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger as log

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


class InventoryDetailsUI(BaseUIService):
    """
    Класс-помощник для рендеринга уровня 2: Карточка предмета.
    """

    def __init__(
        self,
        char_id: int,
        user_id: int,
        state_data: dict[str, Any],
        inventory_service: InventoryService,
    ):
        super().__init__(char_id=char_id, state_data=state_data)
        self.user_id = user_id
        self.inventory_service = inventory_service
        self.InvF = InventoryFormatter
        log.debug(f"InventoryDetailsUI | status=initialized char_id={char_id}")

    async def render(
        self, item_id: int, category: str, page: int, filter_type: str
    ) -> tuple[str, InlineKeyboardMarkup]:
        """
        Рендерит детальную карточку предмета.

        Args:
            item_id: ID предмета.
            category: Текущая категория для кнопки "Назад".
            page: Текущая страница для кнопки "Назад".
            filter_type: Тип фильтра для кнопки "Назад".
        """
        # 🔥 ЧИСТЫЙ ВЫЗОВ Layer 3 (Game Service)
        item = await self.inventory_service.get_item_by_id(item_id)

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
