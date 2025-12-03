from aiogram import Bot, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from app.resources.fsm_states.states import InGame
from app.resources.keyboards.callback_data import MeinMenuCallback
from app.services.core_service.manager.account_manager import AccountManager
from app.services.core_service.manager.world_manager import WorldManager
from app.services.game_service.game_sync_service import GameSyncService
from app.services.game_service.game_world_service import GameWorldService
from app.services.helpers_module.callback_exceptions import UIErrorHandler as Err
from app.services.helpers_module.dto_helper import FSM_CONTEXT_KEY
from app.services.ui_service.inventory.inventory_ui_service import InventoryUIService
from app.services.ui_service.navigation_service import NavigationService

router = Router(name="ui_menu_dispatch")


@router.callback_query(MeinMenuCallback.filter())
async def main_menu_dispatcher(
    call: CallbackQuery,
    callback_data: MeinMenuCallback,
    state: FSMContext,
    bot: Bot,
    session: AsyncSession,
    account_manager: AccountManager,
    world_manager: WorldManager,
    game_world_service: GameWorldService,
) -> None:
    """
    Единая точка входа из Главного Меню.
    Переключает режимы (FSM) и вызывает соответствующие сервисы UI.
    """
    if not call.from_user:
        return

    await call.answer()

    user_id = call.from_user.id
    char_id = callback_data.char_id
    action = callback_data.action

    log.info(f"MenuDispatch | event=action user_id={user_id} char_id={char_id} action='{action}'")

    sync_service = GameSyncService(session, account_manager)
    await sync_service.synchronize_player_state(char_id)
    log.debug(f"StateSync | status=success char_id={char_id}")

    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})

    if session_context.get("char_id") != char_id:
        log.warning(
            f"MenuDispatch | status=failed reason='char_id mismatch' user_id={user_id} expected={char_id} actual={session_context.get('char_id')}"
        )
        await Err.generic_error(call)
        return

    content_msg = session_context.get("message_content")
    if not content_msg:
        log.error(f"MenuDispatch | status=failed reason='message_content not found' user_id={user_id}")
        await Err.message_content_not_found_in_fsm(call)
        return

    chat_id = content_msg["chat_id"]
    message_id = content_msg["message_id"]

    try:
        text, kb = None, None

        if action == "inventory":
            await state.set_state(InGame.inventory)
            log.info(f"FSM | state=InGame.inventory user_id={user_id}")
            service = InventoryUIService(
                char_id=char_id,
                session=session,
                user_id=user_id,
                state_data=state_data,
                account_manager=account_manager,
            )
            text, kb = await service.render_main_menu()

        elif action == "navigation":
            await state.set_state(InGame.navigation)
            log.info(f"FSM | state=InGame.navigation user_id={user_id}")
            nav_service = NavigationService(
                char_id=char_id,
                state_data=state_data,
                account_manager=account_manager,
                world_manager=world_manager,
                game_world_service=game_world_service,
            )
            text, kb = await nav_service.reload_current_ui()

        if text and kb:
            await bot.edit_message_text(
                chat_id=chat_id, message_id=message_id, text=text, reply_markup=kb, parse_mode="HTML"
            )
            log.debug(f"UIRender | component=main_menu status=success user_id={user_id} action='{action}'")
        else:
            log.warning(f"MenuDispatch | status=failed reason='UI data empty' user_id={user_id} action='{action}'")
            await call.answer("Раздел недоступен или пуст.", show_alert=True)

    except RuntimeError:
        log.exception(
            f"MenuDispatch | status=failed reason='RuntimeError in dispatcher' user_id={user_id} action='{action}'"
        )
        await Err.generic_error(call)
