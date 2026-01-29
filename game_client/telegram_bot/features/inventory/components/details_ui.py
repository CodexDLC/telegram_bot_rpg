from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from common.schemas.inventory.enums import InventoryActionType, InventoryViewTarget
from common.schemas.inventory.schemas import DetailsContextDTO, InventoryUIPayloadDTO
from game_client.telegram_bot.base.view_dto import ViewResultDTO
from game_client.telegram_bot.features.inventory.resources.formatters.inventory_formatter import InventoryFormatter
from game_client.telegram_bot.features.inventory.resources.keyboards.callbacks import InventoryActionCB, InventoryViewCB


class DetailsUI:
    """
    Компонент отрисовки экрана 'Детали предмета'.
    """

    def render(self, payload: InventoryUIPayloadDTO) -> ViewResultDTO:
        if not isinstance(payload.context, DetailsContextDTO):
            raise ValueError("Invalid context for DetailsUI")

        text = InventoryFormatter.format_details(payload.context)
        kb = self._build_keyboard(payload.context)

        return ViewResultDTO(text=text, kb=kb)

    def _build_keyboard(self, context: DetailsContextDTO) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()

        # 1. Actions (Equip, Use, Drop)
        for btn in context.actions:
            # Преобразуем строку action в Enum
            try:
                action_enum = InventoryActionType(btn.action)
            except ValueError:
                continue  # Skip unknown actions

            payload_dict = btn.payload or {}

            cb = InventoryActionCB(
                action=action_enum,
                item_id=int(payload_dict.get("item_id") or 0),  # Fix Mypy: Any | None -> int
                slot=payload_dict.get("slot"),
            ).pack()

            builder.button(text=btn.text, callback_data=cb)

        builder.adjust(2)  # Действия по 2 в ряд

        # 2. Back
        if context.back_target:
            target_enum = InventoryViewTarget(context.back_target)
            cb_back = InventoryViewCB(target=target_enum).pack()
            builder.row(InlineKeyboardButton(text="↩️ Назад", callback_data=cb_back))

        return builder.as_markup()
