from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InaccessibleMessage, Message
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from app.resources.fsm_states.states import ArenaState, InGame
from app.resources.keyboards.callback_data import ArenaQueueCallback
from app.resources.schemas_dto.fsm_state_dto import SessionDataDTO
from app.services.game_service.combat.combat_service import CombatService

# 🔥 ТЕПЕРЬ ТОЛЬКО UI ИМПОРТЫ
from app.services.helpers_module.callback_exceptions import UIErrorHandler as Err
from app.services.helpers_module.dto_helper import FSM_CONTEXT_KEY
from app.services.ui_service.arena_ui_service.arena_ui_service import ArenaUIService
from app.services.ui_service.combat.combat_ui_service import CombatUIService
from app.services.ui_service.helpers_ui.ui_animation_service import UIAnimationService

router = Router(name="arena_1v1_router")


@router.callback_query(ArenaState.menu, ArenaQueueCallback.filter(F.action == "match_menu"))
async def arena_1v1_menu_handler(
    call: CallbackQuery,
    callback_data: ArenaQueueCallback,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    if not call.from_user or not call.message or isinstance(call.message, InaccessibleMessage):
        return

    # 1. Init UI (Facade)
    state_data = await state.get_data()
    ui = ArenaUIService(char_id=callback_data.char_id, state_data=state_data, session=session)

    # 2. View
    text, kb = await ui.view_mode_menu(callback_data.match_type)

    if text and kb:
        await call.message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")
        await call.answer()
    else:
        await Err.generic_error(call)


@router.callback_query(ArenaState.menu, ArenaQueueCallback.filter(F.action == "submit_queue_1x1"))
async def arena_submit_queue_handler(
    call: CallbackQuery,
    callback_data: ArenaQueueCallback,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
) -> None:
    if not call.from_user or not call.message or isinstance(call.message, InaccessibleMessage):
        return

    char_id = callback_data.char_id
    user_id = call.from_user.id
    mode = callback_data.match_type

    # 1. Init UI
    state_data = await state.get_data()
    ui = ArenaUIService(char_id, state_data, session)

    # 2. Action (Logic is hidden)
    gs = await ui.action_join_queue(mode)
    if gs is None:
        await Err.generic_error(call)
        return

    # 3. View (Search Screen)
    text, kb = await ui.view_searching_screen(mode, gs)

    # Отправляем UI (и обновляем FSM, чтобы аниматор знал актуальный message_id)
    msg = await call.message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")

    chat_id: int
    message_id: int

    if isinstance(msg, Message):
        chat_id = msg.chat.id
        message_id = msg.message_id
    else:
        chat_id = call.message.chat.id
        message_id = call.message.message_id

    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    session_context["message_content"] = {"chat_id": chat_id, "message_id": message_id}
    await state.update_data({FSM_CONTEXT_KEY: session_context})

    # 4. State Transition
    await state.set_state(ArenaState.waiting)

    # 5. Animation (Polling)
    # Используем DTO из FSM
    session_dto = SessionDataDTO(**session_context)
    anim_service = UIAnimationService(bot, session_dto)

    check_func = ui.get_check_func(mode)  # Получаем функцию проверки из UI сервиса

    session_id = await anim_service.animate_polling(
        base_text=text,
        check_func=check_func,
        steps=10,
        step_delay=3.0,
        fixed_duration=False,
    )

    # 6. Result Handling
    if await state.get_state() != ArenaState.waiting:
        return  # Отмена

    if session_id:
        session_context["combat_session_id"] = session_id
        await state.update_data({FSM_CONTEXT_KEY: session_context})
        state_data[FSM_CONTEXT_KEY] = session_context

        combat_service = CombatService(str(session_id))
        await combat_service.process_turn_updates()
        log.info(f"AI initial move successfully triggered for session {session_id}.")

        # Render Combat
        combat_ui = CombatUIService(user_id, char_id, session_id, state_data)
        text, kb = await combat_ui.render_dashboard(current_selection={})

        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            reply_markup=kb,
            parse_mode="HTML",
        )
        await state.set_state(InGame.combat)
