# app/handlers/callback/ui/inventory/inventory_item_details.py (НОВЫЙ ХЕНДЛЕР)

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from apps.bot.resources.fsm_states.states import InGame
from apps.bot.resources.keyboards.inventory_callback import InventoryCallback
from apps.bot.ui_service.helpers_ui.callback_exceptions import UIErrorHandler as Err
from apps.bot.ui_service.helpers_ui.dto_helper import FSM_CONTEXT_KEY
from apps.bot.ui_service.inventory.inventory_ui_service import InventoryUIService
from apps.common.services.core_service.manager.account_manager import AccountManager

router = Router(name="inventory_item_details")


@router.callback_query(
    InGame.inventory,
    InventoryCallback.filter(F.level == 3),
)
async def inventory_quick_slot_handler(
    call: CallbackQuery,
    callback_data: InventoryCallback,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    account_manager: AccountManager,
) -> None:
    """
    Обрабатывает выбор Quick Slot. (Handler вызывает только публичные методы UI Service).
    """
    if not call.from_user:
        return

    user_id = call.from_user.id
    state_data = await state.get_data()
    char_id = state_data.get(FSM_CONTEXT_KEY, {}).get("char_id")
    item_id = callback_data.item_id
    action = callback_data.action

    if not char_id:
        await Err.char_id_not_found_in_fsm(call)
        return

    log.info(f"InventoryQuickSlot | event=action user_id={user_id} item_id={item_id} action='{action}'")
    await call.answer()

    ui_service = InventoryUIService(
        char_id=char_id, user_id=user_id, session=session, state_data=state_data, account_manager=account_manager
    )
    message_data = ui_service.get_message_content_data()
    if not message_data:
        await Err.message_content_not_found_in_fsm(call)
        return

    chat_id, message_id = message_data

    # --- 1. ACTION: Go to Quick Slot Selection Menu (UI Service renders buttons) ---
    if action == "bind_quick_slot_menu":
        context_data = {
            "category": callback_data.category,
            "page": callback_data.page,
            "filter_type": callback_data.filter_type,
        }
        text, kb = await ui_service.render_quick_slot_selection_menu(item_id, context_data)
        await bot.edit_message_text(
            chat_id=chat_id, message_id=message_id, text=text, reply_markup=kb, parse_mode="HTML"
        )

    # --- 2. ACTION: Bind Item to Selected Slot (UI Service executes action) ---
    elif action == "bind_quick_slot_select":
        quick_slot_key = callback_data.section
        success, msg = await ui_service.action_bind_quick_slot(item_id, quick_slot_key)

        await call.answer(msg, show_alert=True)

        # Rerender Item Details (Level 2)
        text, kb = await ui_service.render_item_details(
            item_id, callback_data.category, callback_data.page, callback_data.filter_type
        )
        await bot.edit_message_text(
            chat_id=chat_id, message_id=message_id, text=text, reply_markup=kb, parse_mode="HTML"
        )

    # --- 3. ACTION: Unbind Item from Slot (UI Service executes action) ---
    elif action == "unbind_quick_slot":
        success, msg = await ui_service.action_unbind_quick_slot(item_id)

        await call.answer(msg, show_alert=True)

        # Rerender Item Details (Level 2)
        text, kb = await ui_service.render_item_details(
            item_id, callback_data.category, callback_data.page, callback_data.filter_type
        )
        await bot.edit_message_text(
            chat_id=chat_id, message_id=message_id, text=text, reply_markup=kb, parse_mode="HTML"
        )
