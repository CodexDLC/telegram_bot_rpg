from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from app.resources.fsm_states.states import InGame
from app.resources.keyboards.inventory_callback import InventoryCallback
from app.services.core_service.manager.account_manager import AccountManager
from app.services.helpers_module.callback_exceptions import UIErrorHandler as Err
from app.services.helpers_module.dto_helper import FSM_CONTEXT_KEY
from app.services.ui_service.inventory.inventory_ui_service import InventoryUIService

router = Router(name="inventory_details_router")


@router.callback_query(
    InGame.inventory,
    InventoryCallback.filter(F.level == 2),
)
async def inventory_item_actions_handler(
    call: CallbackQuery,
    callback_data: InventoryCallback,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    account_manager: AccountManager,
) -> None:
    """Обрабатывает действия с предметами в инвентаре (просмотр, надеть, снять, выбросить)."""
    user_id = call.from_user.id
    if user_id != callback_data.user_id:
        log.warning(f"InventoryItem | status=access_denied user_id={user_id} callback_user_id={callback_data.user_id}")
        await Err.access_denied(call)
        return

    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    char_id = session_context.get("char_id")

    if not char_id:
        log.error(f"InventoryItem | status=failed reason='char_id not found in FSM' user_id={user_id}")
        await Err.char_id_not_found_in_fsm(call)
        return

    service = InventoryUIService(
        char_id=char_id, user_id=user_id, session=session, state_data=state_data, account_manager=account_manager
    )
    item_id = callback_data.item_id
    action = callback_data.action

    log.info(f"InventoryItem | event=action user_id={user_id} char_id={char_id} item_id={item_id} action='{action}'")

    if action == "view":
        pass

    elif action == "equip":
        success, msg = await service.inventory_service.equip_item(item_id)
        if success:
            await call.answer(f"⚔️ {msg}")
            log.info(f"InventoryItem | action=equip status=success user_id={user_id} item_id={item_id}")
        else:
            await call.answer(f"🚫 {msg}", show_alert=True)
            log.warning(
                f"InventoryItem | action=equip status=failed user_id={user_id} item_id={item_id} reason='{msg}'"
            )
            return

    elif action == "unequip":
        success, msg = await service.inventory_service.unequip_item(item_id)
        if success:
            await call.answer(f"🎒 {msg}")
            log.info(f"InventoryItem | action=unequip status=success user_id={user_id} item_id={item_id}")
        else:
            await call.answer(f"🚫 {msg}", show_alert=True)
            log.warning(
                f"InventoryItem | action=unequip status=failed user_id={user_id} item_id={item_id} reason='{msg}'"
            )
            return

    elif action == "drop":
        success = await service.inventory_service.drop_item(item_id)
        if success:
            await call.answer("🗑 Предмет выброшен.")
            log.info(f"InventoryItem | action=drop status=success user_id={user_id} item_id={item_id}")
            text, kb = await service.render_item_list("equip", "all", 0)
            message_data = service.get_message_content_data()
            if message_data:
                await bot.edit_message_text(
                    chat_id=message_data[0], message_id=message_data[1], text=text, reply_markup=kb, parse_mode="HTML"
                )
            return
        else:
            await call.answer("Не удалось выбросить.", show_alert=True)
            log.warning(f"InventoryItem | action=drop status=failed user_id={user_id} item_id={item_id}")
            return

    text, kb = await service.render_item_details(item_id)

    message_data = service.get_message_content_data()
    if not message_data:
        log.error(f"InventoryItem | status=failed reason='message_content not found' user_id={user_id}")
        await Err.generic_error(call)
        return

    try:
        await bot.edit_message_text(
            chat_id=message_data[0], message_id=message_data[1], text=text, reply_markup=kb, parse_mode="HTML"
        )
        log.debug(f"UIRender | component=item_details status=success user_id={user_id} item_id={item_id}")
    except TelegramBadRequest:
        log.debug(f"UIRender | component=item_details status=not_modified user_id={user_id} item_id={item_id}")
        await call.answer()
    except TelegramAPIError:  # Changed from Exception
        log.exception(f"UIRender | component=item_details status=failed user_id={user_id} item_id={item_id}")
