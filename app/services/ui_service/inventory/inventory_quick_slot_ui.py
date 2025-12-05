# app/services/ui_service/inventory/inventory_quick_slot_ui.py
from typing import Any

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger as log

from app.resources.keyboards.inventory_callback import InventoryCallback
from app.resources.schemas_dto.item_dto import QuickSlot
from app.services.game_service.inventory.inventory_service import InventoryService
from app.services.ui_service.base_service import BaseUIService


class InventoryQuickSlotUI(BaseUIService):
    """
    Класс-помощник для рендеринга слотов быстрого доступа.
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
        log.debug(f"InventoryQuickSlotUI | status=initialized char_id={char_id}")

    async def render_belt_overview(self) -> tuple[str, InlineKeyboardMarkup]:
        """
        Рендерит клавиатуру со слотами пояса (1, 2, 3...).
        При нажатии открывается фильтр инвентаря для выбора предмета.
        """
        # 1. Получаем лимит слотов из пояса
        max_slots = await self.inventory_service.get_quick_slot_limit()

        # 2. Получаем текущие предметы в слотах (чтобы отобразить иконки/статус)
        items_in_bag = await self.inventory_service.get_items("inventory")
        slots_content = {}
        for item in items_in_bag:
            if item.quick_slot_position:
                slots_content[item.quick_slot_position] = item

        text = f"🎒 <b>Пояс (Слотов: {max_slots})</b>\nВыберите слот, чтобы положить в него предмет:"
        kb = InlineKeyboardBuilder()

        # 3. Генерируем кнопки 1..N
        for i in range(1, max_slots + 1):
            slot_key = f"quick_slot_{i}"
            item_in_slot = slots_content.get(QuickSlot(slot_key))

            # Текст кнопки: "1: 🔴 Зелье" или "1: Пусто"
            btn_text = f"{i} ⬜️"
            if item_in_slot:
                btn_text = f"{i} ✅ {item_in_slot.data.name}"

            # ACTION: 'open_slot_fill_menu' - открывает список предметов ДЛЯ этого слота
            cb = InventoryCallback(
                level=1,
                user_id=self.user_id,
                section="consumable",  # Мы все еще в разделе расходников
                category="all",
                page=0,
                filter_type=f"assign_to_{slot_key}",  # 🔥 ПЕРЕДАЕМ ЦЕЛЬ: "назначить в слот X"
                action="open_slot_filler",
            ).pack()

            kb.button(text=btn_text, callback_data=cb)

        kb.adjust(2)  # Клавиатура 2xN, как ты просил

        # Кнопка Назад
        cb_back = InventoryCallback(level=0, user_id=self.user_id).pack()
        kb.row(InlineKeyboardButton(text="↩️ Назад", callback_data=cb_back))

        return text, kb.as_markup()

    async def render_quick_slot_selection_menu(
        self, item_id: int, context_data: dict
    ) -> tuple[str, InlineKeyboardMarkup]:
        """СТАРЫЙ МЕТОД (оставляем для совместимости, если нужен при просмотре предмета)"""
        max_slots = await self.inventory_service.get_quick_slot_limit()
        item = await self.inventory_service.get_item_by_id(item_id)
        item_name = item.data.name if item else "Предмет"

        text = f"🔗 <b>Привязать {item_name}</b>\nВыберите слот:"
        kb = InlineKeyboardBuilder()

        for i in range(1, max_slots + 1):
            slot_enum = QuickSlot(f"quick_slot_{i}")
            cb = InventoryCallback(
                level=3,
                user_id=self.user_id,
                action="bind_quick_slot_select",
                item_id=item_id,
                category=context_data.get("category", "all"),
                page=context_data.get("page", 0),
                filter_type=context_data.get("filter_type", "default"),
                section=str(slot_enum.value),
            ).pack()
            kb.button(text=str(i), callback_data=cb)

        kb.adjust(4)
        return text, kb.as_markup()

    async def action_bind(self, item_id: int, quick_slot_key: str) -> tuple[bool, str]:
        """Привязывает предмет к слоту."""
        try:
            slot_enum = QuickSlot(quick_slot_key)
            return await self.inventory_service.move_to_quick_slot(item_id, slot_enum)
        except ValueError:
            return False, "Ошибка слота."

    async def action_unbind(self, item_id: int) -> tuple[bool, str]:
        """Отвязывает предмет."""
        return await self.inventory_service.unbind_quick_slot(item_id)
