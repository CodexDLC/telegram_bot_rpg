# app/services/ui_service/inventory/inventory_main_menu_ui.py
from typing import Any

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger as log

from apps.bot.resources.keyboards.inventory_callback import InventoryCallback
from apps.bot.resources.texts.ui_messages import DEFAULT_ACTOR_NAME
from apps.bot.ui_service.base_service import BaseUIService
from apps.bot.ui_service.helpers_ui.dto.ui_common_dto import ViewResultDTO
from apps.bot.ui_service.inventory.formatters.inventory_formatters import InventoryFormatter
from apps.common.schemas_dto import EquippedSlot, InventoryItemDTO


class InventoryMainMenuUI(BaseUIService):
    """
    Класс-помощник для рендеринга уровня 0: Экран "Кукла персонажа".
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
        # Используем дефолтное имя, так как в BaseUIService его больше нет
        self.actor_name = DEFAULT_ACTOR_NAME
        log.debug(f"InventoryMainMenuUI | status=initialized char_id={char_id}")

    def render(self, summary: dict, equipped: list[InventoryItemDTO]) -> ViewResultDTO:
        """
        Рендерит главный экран 'Кукла персонажа'.
        """
        current_slots = summary.get("weight", 0)  # Временный маппинг, пока не поправим DTO
        max_slots = summary.get("max_weight", 0)
        dust_amount = summary.get("balance", {}).get("dust", 0)  # Предполагаем структуру balance

        text = self.InvF.format_main_menu(
            equipped=equipped, current_slots=current_slots, max_slots=max_slots, dust_amount=dust_amount
        )

        kb = self._kb_main_menu()
        return ViewResultDTO(text=text, kb=kb)

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

        # 2. Кнопки Категорий
        kb_resources = []

        cb_con = InventoryCallback(level=1, user_id=self.user_id, section="consumable", category="all").pack()
        kb_resources.append(InlineKeyboardButton(text=self.InvF.SECTION_NAMES["consumable"], callback_data=cb_con))

        cb_res = InventoryCallback(level=1, user_id=self.user_id, section="resource", category="all").pack()
        kb_resources.append(InlineKeyboardButton(text=self.InvF.SECTION_NAMES["resource"], callback_data=cb_res))

        kb.row(*kb_resources)

        return kb.as_markup()
