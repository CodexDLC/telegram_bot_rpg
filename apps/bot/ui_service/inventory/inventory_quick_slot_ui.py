# app/services/ui_service/inventory/inventory_quick_slot_ui.py
from typing import Any

from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger as log

from apps.bot.resources.keyboards.inventory_callback import InventoryCallback
from apps.bot.resources.texts.ui_messages import DEFAULT_ACTOR_NAME
from apps.bot.ui_service.base_service import BaseUIService
from apps.bot.ui_service.helpers_ui.dto.ui_common_dto import ViewResultDTO
from apps.common.schemas_dto import InventoryItemDTO, QuickSlot


class InventoryQuickSlotUI(BaseUIService):
    """
    Класс-помощник для рендеринга слотов быстрого доступа.
    """

    def __init__(
        self,
        char_id: int,
        user_id: int,
        state_data: dict[str, Any],
    ):
        super().__init__(char_id=char_id, state_data=state_data)
        self.user_id = user_id
        # Используем дефолтное имя, так как в BaseUIService его больше нет
        self.actor_name = DEFAULT_ACTOR_NAME
        log.debug(f"InventoryQuickSlotUI | status=initialized char_id={char_id}")

    def render_belt_overview(self, max_slots: int, items_in_bag: list[InventoryItemDTO]) -> ViewResultDTO:
        """
        Рендерит клавиатуру со слотами пояса (1, 2, 3...).
        """
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

        kb.adjust(2)  # Клавиатура 2xN

        # Кнопка Назад
        cb_back = InventoryCallback(level=0, user_id=self.user_id).pack()
        kb.row(InlineKeyboardButton(text="↩️ Назад", callback_data=cb_back))

        return ViewResultDTO(text=text, kb=kb.as_markup())

    def render_quick_slot_selection_menu(
        self, item_name: str, item_id: int, max_slots: int, context_data: dict
    ) -> ViewResultDTO:
        """Рендерит меню выбора слота для привязки предмета."""
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
        return ViewResultDTO(text=text, kb=kb.as_markup())
