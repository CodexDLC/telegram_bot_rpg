from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InaccessibleMessage, Message
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from apps.bot.resources.fsm_states.states import ArenaState, InGame
from apps.bot.resources.keyboards.callback_data import ArenaQueueCallback
from apps.bot.ui_service.arena_ui_service.arena_ui_service import ArenaUIService
from apps.bot.ui_service.combat.combat_ui_service import CombatUIService
from apps.bot.ui_service.helpers_ui.callback_exceptions import UIErrorHandler as Err
from apps.bot.ui_service.helpers_ui.dto_helper import FSM_CONTEXT_KEY
from apps.bot.ui_service.helpers_ui.ui_animation_service import UIAnimationService
from apps.common.schemas_dto import SessionDataDTO
from apps.common.services.core_service.manager.account_manager import AccountManager
from apps.common.services.core_service.manager.arena_manager import ArenaManager
from apps.common.services.core_service.manager.combat_manager import CombatManager
from apps.game_core.game_service.combat.combat_service import CombatService

router = Router(name="arena_1v1_router")


@router.callback_query(ArenaState.menu, ArenaQueueCallback.filter(F.action == "match_menu"))
async def arena_1v1_menu_handler(
    call: CallbackQuery,
    callback_data: ArenaQueueCallback,
    state: FSMContext,
    session: AsyncSession,
    account_manager: AccountManager,
    arena_manager: ArenaManager,
    combat_manager: CombatManager,
) -> None:
    """Отображает меню выбора режима арены."""
    if not call.from_user or not call.message or isinstance(call.message, InaccessibleMessage):
        return

    char_id = callback_data.char_id
    user_id = call.from_user.id
    mode = callback_data.match_type
    log.info(f"Arena | event=view_mode_menu user_id={user_id} char_id={char_id} mode='{mode}'")

    state_data = await state.get_data()
    ui = ArenaUIService(
        char_id=char_id,
        state_data=state_data,
        session=session,
        account_manager=account_manager,
        arena_manager=arena_manager,
        combat_manager=combat_manager,
    )
    text, kb = await ui.view_mode_menu(mode)

    if text and kb:
        await call.message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")
        await call.answer()
    else:
        log.error(f"Arena | status=failed reason='view_mode_menu returned None' user_id={user_id}")
        await Err.generic_error(call)


@router.callback_query(ArenaState.menu, ArenaQueueCallback.filter(F.action == "submit_queue_1x1"))
async def arena_submit_queue_handler(
    call: CallbackQuery,
    callback_data: ArenaQueueCallback,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    account_manager: AccountManager,
    arena_manager: ArenaManager,
    combat_manager: CombatManager,
) -> None:
    """Обрабатывает вход в очередь на арене и запускает поиск матча."""
    if not call.from_user or not call.message or isinstance(call.message, InaccessibleMessage):
        return

    char_id = callback_data.char_id
    user_id = call.from_user.id
    mode = callback_data.match_type
    log.info(f"Arena | event=join_queue user_id={user_id} char_id={char_id} mode='{mode}'")

    state_data = await state.get_data()
    ui = ArenaUIService(char_id, state_data, session, account_manager, arena_manager, combat_manager)
    gs = await ui.action_join_queue(mode)
    if gs is None:
        log.error(f"Arena | status=failed reason='action_join_queue returned None' user_id={user_id}")
        await Err.generic_error(call)
        return

    text, kb = await ui.view_searching_screen(mode, gs)
    msg = await call.message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")

    chat_id = msg.chat.id if isinstance(msg, Message) else call.message.chat.id
    message_id = msg.message_id if isinstance(msg, Message) else call.message.message_id

    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    session_context["message_content"] = {"chat_id": chat_id, "message_id": message_id}
    await state.update_data({FSM_CONTEXT_KEY: session_context})
    await state.set_state(ArenaState.waiting)
    log.info(f"FSM | state=ArenaState.waiting user_id={user_id}")

    session_dto = SessionDataDTO(**session_context)
    anim_service = UIAnimationService(bot, session_dto)
    check_func = ui.get_check_func(mode)

    session_id = await anim_service.animate_polling(
        base_text=text, check_func=check_func, steps=10, step_delay=3.0, fixed_duration=False
    )

    if await state.get_state() != ArenaState.waiting:
        log.info(f"Arena | event=polling_cancelled user_id={user_id} state='{await state.get_state()}'")
        return

    if not session_id:
        log.info(f"Arena | event=match_not_found_creating_shadow user_id={user_id}")
        session_id = await ui.action_create_shadow_battle(mode)

    if session_id:
        log.info(f"Arena | event=match_found_or_shadow_created user_id={user_id} session_id='{session_id}'")
        session_context["combat_session_id"] = session_id
        await state.update_data({FSM_CONTEXT_KEY: session_context})
        state_data[FSM_CONTEXT_KEY] = session_context

        combat_service = CombatService(str(session_id), combat_manager, account_manager)
        await combat_service.process_turn_updates()
        log.info(f"Combat | event=ai_initial_move status=triggered session_id='{session_id}'")

        combat_ui = CombatUIService(user_id, char_id, session_id, state_data, combat_manager, account_manager)
        text, kb = await combat_ui.render_dashboard(current_selection={})

        await bot.edit_message_text(
            chat_id=chat_id, message_id=message_id, text=text, reply_markup=kb, parse_mode="HTML"
        )
        await state.set_state(InGame.combat)
        log.info(f"FSM | state=InGame.combat user_id={user_id}")
    else:
        log.error(f"Arena | event=shadow_battle_creation_failed user_id={user_id}")
        await call.message.edit_text("Не удалось создать бой с тенью. Попробуйте позже.")
        await state.set_state(ArenaState.menu)
