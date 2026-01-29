from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from common.schemas.inventory.enums import InventoryViewTarget
from common.schemas.inventory.schemas import BagContextDTO, InventoryUIPayloadDTO
from game_client.telegram_bot.base.view_dto import ViewResultDTO
from game_client.telegram_bot.features.inventory.resources.formatters.inventory_formatter import InventoryFormatter
from game_client.telegram_bot.features.inventory.resources.keyboards.callbacks import InventoryViewCB


class BagUI:
    """
    Компонент отрисовки экрана 'Сумка' (Сетка предметов).
    """

    GRID_SIZE = 9  # 3x3

    def render(self, payload: InventoryUIPayloadDTO) -> ViewResultDTO:
        if not isinstance(payload.context, BagContextDTO):
            raise ValueError("Invalid context for BagUI")

        text = InventoryFormatter.format_bag(payload.context)
        kb = self._build_keyboard(payload.context, payload.navigation_buttons)

        return ViewResultDTO(text=text, kb=kb)

    def _build_keyboard(self, context: BagContextDTO, nav_buttons: list) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()

        # 1. Сетка предметов (3x3)
        for i in range(self.GRID_SIZE):
            if i < len(context.items):
                item = context.items[i]
                text = str(i + 1)
                cb = InventoryViewCB(target=InventoryViewTarget.DETAILS, item_id=item.inventory_id).pack()
                builder.button(text=text, callback_data=cb)
            else:
                builder.button(text=" ", callback_data="ignore")

        builder.adjust(3)

        # 2. Пагинация
        pag = context.pagination
        pag_row = []

        # Используем str() для Enum, чтобы избежать проблем с типами
        section_str = str(context.active_section)

        # Prev
        if pag.has_prev:
            cb_prev = InventoryViewCB(
                target=InventoryViewTarget.BAG, section=section_str, category=context.active_category, page=pag.page - 1
            ).pack()
            pag_row.append(InlineKeyboardButton(text="◀️", callback_data=cb_prev))
        else:
            pag_row.append(InlineKeyboardButton(text=" ", callback_data="ignore"))

        # Counter
        pag_row.append(InlineKeyboardButton(text=f"{pag.page + 1}/{pag.total_pages}", callback_data="ignore"))

        # Next
        if pag.has_next:
            cb_next = InventoryViewCB(
                target=InventoryViewTarget.BAG, section=section_str, category=context.active_category, page=pag.page + 1
            ).pack()
            pag_row.append(InlineKeyboardButton(text="▶️", callback_data=cb_next))
        else:
            pag_row.append(InlineKeyboardButton(text=" ", callback_data="ignore"))

        builder.row(*pag_row)

        # 3. Фильтры (Категории)
        for btn in nav_buttons:
            text = f"✅ {btn.text}" if btn.is_active else btn.text

            target_enum = InventoryViewTarget(btn.action)

            cb = InventoryViewCB(
                target=target_enum, section=btn.payload.get("section"), category=btn.payload.get("category")
            ).pack()
            builder.button(text=text, callback_data=cb)

        builder.adjust(3)

        # 4. Назад
        if context.back_target:
            target_enum = InventoryViewTarget(context.back_target)
            cb_back = InventoryViewCB(target=target_enum).pack()
            builder.row(InlineKeyboardButton(text="↩️ Назад", callback_data=cb_back))

        return builder.as_markup()
