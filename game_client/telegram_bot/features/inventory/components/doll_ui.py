from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from common.schemas.inventory.enums import InventorySection, InventoryViewTarget
from common.schemas.inventory.schemas import DollContextDTO, InventoryUIPayloadDTO
from common.schemas.item import EquippedSlot
from game_client.telegram_bot.base.view_dto import ViewResultDTO
from game_client.telegram_bot.features.inventory.resources.formatters.inventory_formatter import InventoryFormatter
from game_client.telegram_bot.features.inventory.resources.keyboards.callbacks import InventoryViewCB


class DollUI:
    """
    Компонент отрисовки экрана 'Кукла'.
    """

    def render(self, payload: InventoryUIPayloadDTO) -> ViewResultDTO:
        if not isinstance(payload.context, DollContextDTO):
            raise ValueError("Invalid context for DollUI")

        # Текст формируется форматтером (список слотов + статы)
        text = InventoryFormatter.format_doll(payload.context)
        kb = self._build_keyboard(payload.context, payload.navigation_buttons)

        return ViewResultDTO(text=text, kb=kb)

    def _build_keyboard(self, context: DollContextDTO, nav_buttons: list) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()

        # 1. Сетка слотов (Анатомическая)
        layout = [
            [EquippedSlot.EARRING, EquippedSlot.HEAD_ARMOR, EquippedSlot.AMULET],
            [EquippedSlot.ARMS_ARMOR, EquippedSlot.CHEST_ARMOR, EquippedSlot.OUTER_GARMENT],
            [EquippedSlot.MAIN_HAND, EquippedSlot.BELT_ACCESSORY, EquippedSlot.OFF_HAND],
            [EquippedSlot.GLOVES_GARMENT, EquippedSlot.LEGS_ARMOR, EquippedSlot.RING_1],
            [EquippedSlot.RING_2, EquippedSlot.FEET_ARMOR, EquippedSlot.CHEST_GARMENT],
        ]

        for row in layout:
            for slot in row:
                item = context.equipped_items.get(slot)

                if item:
                    # Если есть предмет: Только иконка (для ровной сетки)
                    icon = InventoryFormatter._get_rarity_icon(item.rarity)
                    text = f"{icon}"

                    # Клик по предмету -> Детали
                    cb = InventoryViewCB(target=InventoryViewTarget.DETAILS, item_id=item.inventory_id).pack()
                else:
                    # Пустой слот: Пустые скобки (для ровной сетки)
                    text = "[ ]"

                    # Клик по пустому слоту -> Сумка с фильтром по этому слоту
                    cb = InventoryViewCB(
                        target=InventoryViewTarget.BAG, section=InventorySection.EQUIPMENT.value, category=slot.value
                    ).pack()

                builder.button(text=text, callback_data=cb)
            builder.row()

        # 2. Навигация (Рюкзак, Ресурсы)
        for btn in nav_buttons:
            cb = InventoryViewCB(
                target=btn.action, section=btn.payload.get("section"), category=btn.payload.get("category")
            ).pack()

            builder.button(text=btn.text, callback_data=cb)

        builder.adjust(3)  # Выравнивание навигации

        return builder.as_markup()
