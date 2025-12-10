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

router = Router(name="inventory_resource_router")


@router.callback_query(
    InGame.inventory,
    InventoryCallback.filter((F.section == "resource") & (F.level == 1)),
)
async def inventory_resource_list_handler(
    call: CallbackQuery,
    callback_data: InventoryCallback,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    account_manager: AccountManager,
) -> None:
    """Обрабатывает список ресурсов, фильтры и пагинацию."""
    user_id = call.from_user.id
    if user_id != callback_data.user_id:
        log.warning(
            f"InventoryResource | status=access_denied user_id={user_id} callback_user_id={callback_data.user_id}"
        )
        await Err.access_denied(call)
        return

    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    char_id = session_context.get("char_id")

    if not char_id:
        log.error(f"InventoryResource | status=failed reason='char_id not found in FSM' user_id={user_id}")
        await Err.char_id_not_found_in_fsm(call)
        return

    service = InventoryUIService(
        char_id=char_id, user_id=user_id, session=session, state_data=state_data, account_manager=account_manager
    )
    text, kb = await service.render_item_list(
        section="resource", category=callback_data.category, page=callback_data.page
    )

    message_data = service.get_message_content_data()
    if not message_data:
        log.error(f"InventoryResource | status=failed reason='message_content not found' user_id={user_id}")
        await Err.generic_error(call)
        return

    chat_id, message_id = message_data
    await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=kb, parse_mode="HTML")
    await call.answer()
    log.info(
        f"InventoryResource | event=list_rendered user_id={user_id} char_id={char_id} category='{callback_data.category}' page={callback_data.page}"
    )
