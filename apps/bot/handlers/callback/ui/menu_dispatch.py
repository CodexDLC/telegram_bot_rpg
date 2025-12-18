# apps/bot/handlers/callback/ui/menu_dispatch.py
from aiogram import Bot, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from apps.bot.resources.fsm_states.states import InGame
from apps.bot.resources.keyboards.callback_data import MeinMenuCallback
from apps.bot.ui_service.exploration.exploration_ui import ExplorationUIService  # ИЗМЕНЕНО
from apps.bot.ui_service.helpers_ui.callback_exceptions import UIErrorHandler as Err
from apps.bot.ui_service.helpers_ui.dto_helper import FSM_CONTEXT_KEY
from apps.bot.ui_service.inventory.inventory_ui_service import InventoryUIService
from apps.bot.ui_service.menu_service import MenuService
from apps.common.services.core_service.manager.account_manager import AccountManager
from apps.game_core.game_service.game_sync_service import GameSyncService

router = Router(name="ui_menu_dispatch")


@router.callback_query(MeinMenuCallback.filter())
async def main_menu_dispatcher(
    call: CallbackQuery,
    callback_data: MeinMenuCallback,
    state: FSMContext,
    bot: Bot,
    session: AsyncSession,
    account_manager: AccountManager,
    exploration_ui_service: ExplorationUIService,  # ИЗМЕНЕНО
) -> None:
    if not call.from_user:
        return
    if callback_data.action != "refresh_menu":
        await call.answer()
    user_id = call.from_user.id
    char_id = callback_data.char_id
    action = callback_data.action
    log.info(f"MenuDispatch | event=action user_id={user_id} char_id={char_id} action='{action}'")
    sync_service = GameSyncService(session, account_manager)
    await sync_service.synchronize_player_state(char_id)
    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    if session_context.get("char_id") != char_id:
        await Err.generic_error(call)
        return
    if action == "refresh_menu":
        menu_msg = session_context.get("message_menu")
        if not menu_msg:
            await Err.message_content_not_found_in_fsm(call)
            return
        await call.answer("🔄 Обновление данных...")
        menu_service = MenuService(
            game_stage="in_game", state_data=state_data, session=session, account_manager=account_manager
        )
        final_text, final_kb = await menu_service.run_full_refresh_action()
        try:
            await bot.edit_message_text(
                chat_id=menu_msg["chat_id"],
                message_id=menu_msg["message_id"],
                text=final_text,
                reply_markup=final_kb,
                parse_mode="HTML",
            )
        except TelegramAPIError as e:
            log.warning(f"RefreshMenu | status=edit_failed error='{e}'")
        return
    content_msg = session_context.get("message_content")
    if not content_msg:
        await Err.generic_error(call)
        return
    chat_id = content_msg["chat_id"]
    message_id = content_msg["message_id"]
    try:
        text, kb = None, None
        if action == "inventory":
            await state.set_state(InGame.inventory)
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
            actor_name = session_context.get("symbiote_name", "Симбиот")
            text, kb = await exploration_ui_service.render_map(  # ИЗМЕНЕНО
                char_id=char_id, actor_name=actor_name
            )
        if text and kb:
            await bot.edit_message_text(
                chat_id=chat_id, message_id=message_id, text=text, reply_markup=kb, parse_mode="HTML"
            )
        else:
            await call.answer("Раздел недоступен.", show_alert=True)
    except (TelegramAPIError, ValueError) as e:
        log.exception(f"MenuDispatch | status=failed action='{action}' error='{e}'")
        await Err.generic_error(call)
