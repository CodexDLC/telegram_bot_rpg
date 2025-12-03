from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from app.resources.fsm_states.states import ArenaState, InGame
from app.resources.keyboards.callback_data import ArenaQueueCallback
from app.services.core_service.manager.account_manager import AccountManager
from app.services.core_service.manager.arena_manager import ArenaManager
from app.services.core_service.manager.combat_manager import CombatManager
from app.services.core_service.manager.world_manager import WorldManager
from app.services.game_service.game_world_service import GameWorldService
from app.services.helpers_module.callback_exceptions import UIErrorHandler as Err
from app.services.helpers_module.dto_helper import FSM_CONTEXT_KEY
from app.services.ui_service.arena_ui_service.arena_ui_service import ArenaUIService
from app.services.ui_service.navigation_service import NavigationService

router = Router(name="arena_main_router")


@router.callback_query(ArenaState.menu, ArenaQueueCallback.filter(F.action == "menu_main"))
async def arena_render_main_menu_handler(
    call: CallbackQuery,
    callback_data: ArenaQueueCallback,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    account_manager: AccountManager,
    arena_manager: ArenaManager,
    combat_manager: CombatManager,
) -> None:
    """Отображает главное меню Арены."""
    if not call.from_user:
        return

    char_id = callback_data.char_id
    user_id = call.from_user.id
    log.info(f"Arena | event=view_main_menu user_id={user_id} char_id={char_id}")

    state_data = await state.get_data()
    ui = ArenaUIService(char_id, state_data, session, account_manager, arena_manager, combat_manager)
    text, kb = await ui.view_main_menu()

    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    message_content = session_context.get("message_content")

    if message_content and text and kb:
        await bot.edit_message_text(
            chat_id=message_content["chat_id"],
            message_id=message_content["message_id"],
            text=text,
            reply_markup=kb,
            parse_mode="HTML",
        )
        await call.answer()
    else:
        log.error(f"Arena | status=failed reason='message_content or view data missing' user_id={user_id}")
        await Err.message_content_not_found_in_fsm(call)


@router.callback_query(ArenaState.menu, ArenaQueueCallback.filter(F.action == "exit_service"))
async def arena_exit_service_handler(
    call: CallbackQuery,
    callback_data: ArenaQueueCallback,
    state: FSMContext,
    bot: Bot,
    account_manager: AccountManager,
    world_manager: WorldManager,
    game_world_service: GameWorldService,
) -> None:
    """Обрабатывает выход из Арены и возврат в мир."""
    if not call.from_user:
        return

    user_id = call.from_user.id
    char_id = callback_data.char_id
    log.info(f"Arena | event=exit_service user_id={user_id} char_id={char_id}")
    await call.answer("Вы покидаете Полигон.")

    await state.set_state(InGame.navigation)
    log.info(f"FSM | state=InGame.navigation user_id={user_id}")

    state_data = await state.get_data()
    nav_service = NavigationService(
        char_id=char_id,
        state_data=state_data,
        account_manager=account_manager,
        world_manager=world_manager,
        game_world_service=game_world_service,
    )
    text, kb = await nav_service.reload_current_ui()

    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    message_content = session_context.get("message_content")

    if message_content and text and kb:
        await bot.edit_message_text(
            chat_id=message_content["chat_id"],
            message_id=message_content["message_id"],
            text=text,
            parse_mode="html",
            reply_markup=kb,
        )
    else:
        log.error(f"Arena | status=failed reason='Could not render navigation UI on exit' user_id={user_id}")
        await Err.generic_error(call)


@router.callback_query(ArenaState.waiting, ArenaQueueCallback.filter(F.action == "cancel_queue"))
async def arena_universal_cancel_handler(
    call: CallbackQuery,
    callback_data: ArenaQueueCallback,
    state: FSMContext,
    session: AsyncSession,
    account_manager: AccountManager,
    arena_manager: ArenaManager,
    combat_manager: CombatManager,
) -> None:
    """Обрабатывает отмену поиска матча на Арене."""
    if not call.from_user:
        return

    char_id = callback_data.char_id
    user_id = call.from_user.id
    mode = callback_data.match_type
    log.info(f"Arena | event=cancel_queue user_id={user_id} char_id={char_id} mode='{mode}'")

    state_data = await state.get_data()
    ui = ArenaUIService(char_id, state_data, session, account_manager, arena_manager, combat_manager)
    await ui.action_cancel_queue(mode)
    await state.set_state(ArenaState.menu)
    log.info(f"FSM | state=ArenaState.menu user_id={user_id}")

    text, kb = await ui.view_mode_menu(mode)

    if text and kb and isinstance(call.message, Message):
        await call.message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")
        await call.answer("Поиск отменен.")
    else:
        log.error(f"Arena | status=failed reason='Could not render mode menu on cancel' user_id={user_id}")
        await Err.generic_error(call)
