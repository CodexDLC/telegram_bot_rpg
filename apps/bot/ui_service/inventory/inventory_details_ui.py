# app/services/ui_service/inventory/inventory_details_ui.py
from typing import Any

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger as log

from apps.bot.resources.keyboards.inventory_callback import InventoryCallback
from apps.bot.ui_service.base_service import BaseUIService
from apps.bot.ui_service.helpers_ui.dto.ui_common_dto import ViewResultDTO
from apps.bot.ui_service.helpers_ui.formatters.inventory_formatters import InventoryFormatter
from apps.common.schemas_dto import InventoryItemDTO, ItemType

SECTION_TYPE_MAP = {
    "equip": [ItemType.WEAPON, ItemType.ARMOR, ItemType.ACCESSORY],
    "resource": [ItemType.RESOURCE, ItemType.CURRENCY],
    "consumable": [ItemType.CONSUMABLE],
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
    ):
        super().__init__(char_id=char_id, state_data=state_data)
        self.user_id = user_id
        self.InvF = InventoryFormatter
        log.debug(f"InventoryDetailsUI | status=initialized char_id={char_id}")

    def render(
        self,
        item: InventoryItemDTO,
        comparison_data: dict | None,
        category: str,
        page: int,
        filter_type: str,
    ) -> ViewResultDTO:
        """
        Рендерит детальную карточку предмета.
        """
        # 1. Генерируем базовое описание
        details_text = self.InvF.format_item_details(item, actor_name="📦 Инфо")

        # 2. Генерируем Блок Сравнения
        comparison_block = self._format_comparison_block(comparison_data)

        # 3. Собираем итоговый текст
        full_text = f"{details_text}\n{comparison_block}"

        # 4. Клавиатура действий
        kb = self._kb_item_details(item, category, page, filter_type)

        return ViewResultDTO(text=full_text, kb=kb)

    def _format_comparison_block(self, comparison_data: dict | None) -> str:
        """
        Форматирует блок сравнения на основе данных.
        """
        # FIXME [ARCH-DEBT]: Перенести расчет дельты характеристик в CoreOrchestrator.
        # UI не должен знать формулы. Он должен получить от бэкенда готовое: {"atk": {"old": 10, "new": 15, "diff": 5}}.
        if not comparison_data:
            return ""

        if comparison_data.get("is_empty"):
            return "\n⚖️ <b>Сравнение:</b>\n<i>Слот свободен. Чистая прибавка.</i>"

        diffs = comparison_data.get("diffs", {})
        old_name = comparison_data.get("old_item_name", "???")

        if not diffs:
            return "\n⚖️ <b>Сравнение:</b>\n<i>Характеристики идентичны.</i>"

        diff_lines = []
        for stat, diff in diffs.items():
            sign = "+" if diff > 0 else ""
            icon = "🟢" if diff > 0 else "🔴"
            stat_name = stat.replace("_", " ").capitalize()
            diff_lines.append(f"{icon} {stat_name}: {sign}{diff}")

        return "\n⚖️ <b>Сравнение</b> (с " + old_name + "):\n<code>" + "\n".join(diff_lines) + "</code>"

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
