# app/services/ui_service/inventory/inventory_main_menu_ui.py
from typing import Any

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger as log

from app.resources.keyboards.inventory_callback import InventoryCallback
from app.resources.schemas_dto.item_dto import EquippedSlot
from app.services.game_service.inventory.inventory_service import InventoryService
from app.services.ui_service.base_service import BaseUIService
from app.services.ui_service.helpers_ui.inventory_formatters import InventoryFormatter


class InventoryMainMenuUI(BaseUIService):
    """
    Класс-помощник для рендеринга уровня 0: Экран "Кукла персонажа".
    Отвечает за сбор данных об экипировке и формирование главной клавиатуры.
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
        log.debug(f"InventoryMainMenuUI | status=initialized char_id={char_id}")

    async def render(self) -> tuple[str, InlineKeyboardMarkup]:
        """
        Рендерит главный экран 'Кукла персонажа'.
        """
        # 🔥 ЧИСТЫЙ ВЫЗОВ Layer 3 (Game Service)
        equipped = await self.inventory_service.get_items("equipped")
        current_slots, max_slots = await self.inventory_service.get_capacity()
        dust_amount = await self.inventory_service.get_dust_amount()

        text = self.InvF.format_main_menu(
            equipped=equipped, current_slots=current_slots, max_slots=max_slots, dust_amount=dust_amount
        )

        kb = self._kb_main_menu()
        return text, kb

    def _kb_main_menu(self) -> InlineKeyboardMarkup:
        """
        Клавиатура Уровня 0: Экран Куклы.
        """
        kb = InlineKeyboardBuilder()

        # Список слотов в том порядке, в котором они должны быть на клавиатуре (3 колонки)
        slot_button_order = [
            (EquippedSlot.HEAD_ARMOR, EquippedSlot.CHEST_GARMENT, EquippedSlot.AMULET),
            (EquippedSlot.CHEST_ARMOR, EquippedSlot.OUTER_GARMENT, EquippedSlot.BELT_ACCESSORY),
            (EquippedSlot.MAIN_HAND, EquippedSlot.OFF_HAND, EquippedSlot.TWO_HAND),
            (EquippedSlot.LEGS_ARMOR, EquippedSlot.FEET_ARMOR, EquippedSlot.RING_1),
            (EquippedSlot.ARMS_ARMOR, EquippedSlot.GLOVES_GARMENT, EquippedSlot.RING_2),
        ]

        # 1. Сетка слотов Куклы
        for row in slot_button_order:
            row_buttons = []
            for slot_enum in row:
                full_name = self.InvF.SLOT_NAMES.get(slot_enum.value, slot_enum.name)
                short_text = full_name.split()[0]

                # КОНТРАКТ: level=1, section='equip', category=slot_enum.value, filter_type='slot'
                callback_data = InventoryCallback(
                    level=1,
                    user_id=self.user_id,
                    section="equip",
                    category=str(slot_enum.value),
                    filter_type="slot",
                    page=0,
                ).pack()

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
