# app/handlers/callback/ui/inventory/inventory_main.py
from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from app.resources.fsm_states.states import InGame
from app.resources.keyboards.inventory_callback import InventoryCallback
from app.services.helpers_module.callback_exceptions import UIErrorHandler as Err
from app.services.helpers_module.dto_helper import FSM_CONTEXT_KEY
from app.services.ui_service.inventory.inventory_ui_service import InventoryUIService

router = Router(name="inventory_main_router")


@router.callback_query(
    InGame.inventory,
    InventoryCallback.filter(F.level == 0),
)
async def inventory_main_handler(
    call: CallbackQuery,
    callback_data: InventoryCallback,  # Aiogram сам распарсил колбэк
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
) -> None:
    #  1. SECURITY CHECK
    # Сравниваем ID того, кто нажал (from_user.id)
    # с ID владельца кнопки (callback_data.user_id)
    if call.from_user.id != callback_data.user_id:
        log.warning(f"Попытка поденный данных user_id = {callback_data.user_id}")
        await Err.access_denied(call)
        return

    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    user_id = session_context.get("user_id") or call.from_user.id
    char_id = session_context.get("char_id")

    service = InventoryUIService(char_id=char_id, session=session, state_data=state_data, user_id=user_id)

    text, kb = await service.render_main_menu()

    message_data = service.get_message_content_data()
    if not message_data:
        await Err.generic_error(call)
        return

    chat_id, message_id = message_data

    await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=kb, parse_mode="HTML")
