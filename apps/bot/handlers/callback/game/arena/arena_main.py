# apps/bot/handlers/callback/game/arena/arena_main.py
from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger as log

from apps.bot.resources.fsm_states.states import ArenaState, InGame
from apps.bot.resources.keyboards.callback_data import ArenaQueueCallback
from apps.bot.ui_service.arena_ui_service.arena_ui_service import ArenaUIService
from apps.bot.ui_service.exploration.exploration_ui import ExplorationUIService
from apps.bot.ui_service.helpers_ui.callback_exceptions import UIErrorHandler as Err
from apps.bot.ui_service.helpers_ui.dto_helper import FSM_CONTEXT_KEY

router = Router(name="arena_main_router")


@router.callback_query(ArenaState.menu, ArenaQueueCallback.filter(F.action == "menu_main"))
async def arena_render_main_menu_handler(
    call: CallbackQuery,
    callback_data: ArenaQueueCallback,
    state: FSMContext,
    bot: Bot,
) -> None:
    if not call.from_user:
        return
    char_id = callback_data.char_id
    user_id = call.from_user.id
    log.info(f"Arena | event=view_main_menu user_id={user_id} char_id={char_id}")
    state_data = await state.get_data()
    actor_name = state_data.get(FSM_CONTEXT_KEY, {}).get("symbiote_name", "Симбиот")
    ui = ArenaUIService(char_id, actor_name)
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
    exploration_ui_service: ExplorationUIService,
) -> None:
    if not call.from_user:
        return
    user_id = call.from_user.id
    char_id = callback_data.char_id
    log.info(f"Arena | event=exit_service user_id={user_id} char_id={char_id}")
    await call.answer("Вы покидаете Полигон.")
    await state.set_state(InGame.navigation)
    log.info(f"FSM | state=InGame.navigation user_id={user_id}")
    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    message_content = session_context.get("message_content")
    actor_name = session_context.get("symbiote_name", "Симбиот")

    text, kb = await exploration_ui_service.render_map(char_id=char_id, actor_name=actor_name)

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
