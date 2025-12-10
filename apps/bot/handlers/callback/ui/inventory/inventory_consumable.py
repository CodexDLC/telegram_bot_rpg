# app/handlers/callback/ui/inventory/inventory_consumable.py
from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from apps.bot.resources.fsm_states.states import InGame
from apps.bot.resources.keyboards.inventory_callback import InventoryCallback
from apps.bot.ui_service.helpers_ui.callback_exceptions import UIErrorHandler as Err
from apps.bot.ui_service.helpers_ui.dto_helper import FSM_CONTEXT_KEY
from apps.bot.ui_service.inventory.inventory_ui_service import InventoryUIService
from apps.common.services.core_service.manager.account_manager import AccountManager

router = Router(name="inventory_consumable_router")


# 1. ОБРАБОТЧИК КНОПКИ "РАСХОДНИКИ" -> ОТКРЫВАЕТ ПОЯС
@router.callback_query(
    InGame.inventory,
    InventoryCallback.filter((F.section == "consumable") & (F.level == 1) & (F.action != "open_slot_filler")),
)
async def inventory_belt_view_handler(
    call: CallbackQuery,
    callback_data: InventoryCallback,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    account_manager: AccountManager,
) -> None:
    user_id = call.from_user.id
    state_data = await state.get_data()
    char_id = state_data.get(FSM_CONTEXT_KEY, {}).get("char_id")

    if not char_id:
        await Err.char_id_not_found_in_fsm(call)
        return

    service = InventoryUIService(char_id, user_id, session, state_data, account_manager)

    # 🔥 Рендерим именно ПОЯС (кнопки 1, 2, 3...)
    text, kb = await service.render_belt_overview()

    message_data = service.get_message_content_data()
    if message_data:
        chat_id, message_id = message_data
        await bot.edit_message_text(
            chat_id=chat_id, message_id=message_id, text=text, reply_markup=kb, parse_mode="HTML"
        )
    await call.answer()


# 2. ОБРАБОТЧИК НАЖАТИЯ НА ЦИФРУ СЛОТА -> ОТКРЫВАЕТ СПИСОК ПРЕДМЕТОВ
@router.callback_query(
    InGame.inventory,
    InventoryCallback.filter(F.action == "open_slot_filler"),
)
async def inventory_fill_slot_handler(
    call: CallbackQuery,
    callback_data: InventoryCallback,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    account_manager: AccountManager,
) -> None:
    user_id = call.from_user.id
    state_data = await state.get_data()
    char_id = state_data.get(FSM_CONTEXT_KEY, {}).get("char_id")

    service = InventoryUIService(char_id, user_id, session, state_data, account_manager)

    # Мы передали "assign_to_quick_slot_1" в поле filter_type
    target_slot = callback_data.filter_type

    # Теперь открываем ОБЫЧНЫЙ СПИСОК, но с особым filter_type
    text, kb = await service.render_item_list(
        section="consumable",
        category="all",
        page=callback_data.page,
        filter_type=target_slot,  # Это важно! UI списка поймет, что мы выбираем предмет для слота
    )

    message_data = service.get_message_content_data()
    if message_data:
        chat_id, message_id = message_data
        await bot.edit_message_text(
            chat_id=chat_id, message_id=message_id, text=text, reply_markup=kb, parse_mode="HTML"
        )
    await call.answer()
