import asyncio
import time

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from apps.bot.resources.fsm_states.states import StartTutorial
from apps.bot.ui_service.helpers_ui.callback_exceptions import UIErrorHandler as Err
from apps.bot.ui_service.helpers_ui.dto_helper import FSM_CONTEXT_KEY
from apps.bot.ui_service.helpers_ui.ui_animation_service import UIAnimationService
from apps.bot.ui_service.helpers_ui.ui_tools import await_min_delay
from apps.bot.ui_service.tutorial.tutorial_service import TutorialServiceStats
from apps.common.schemas_dto import SessionDataDTO

router = Router(name="tutorial_game_router")


@router.callback_query(StartTutorial.start, F.data.startswith("tut:start"))
async def start_tutorial_handler(call: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    """Начинает туториал по распределению очков характеристик."""
    if not call.from_user:
        return

    user_id = call.from_user.id
    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    char_id = session_context.get("char_id")
    log.info(f"TutorialStats | event=start user_id={user_id} char_id={char_id}")
    await call.answer()

    if not isinstance(char_id, int):
        log.warning(f"TutorialStats | status=failed reason='Invalid char_id in FSM' user_id={user_id}")
        await Err.invalid_id(call=call)
        return

    tut_service = TutorialServiceStats(char_id=char_id, bonus_dict={})
    next_step_data = tut_service.get_next_step()
    if next_step_data is None:
        log.error(f"TutorialStats | status=failed reason='get_next_step returned None on first step' char_id={char_id}")
        await Err.callback_data_missing(call)
        return

    text, kb = next_step_data
    log.debug(f"TutorialStats | step=initial_render user_id={user_id}")

    message_content = session_context.get("message_content")
    if not isinstance(message_content, dict):
        log.error(f"TutorialStats | status=failed reason='message_content not found in FSM' user_id={user_id}")
        await Err.message_content_not_found_in_fsm(call=call)
        return

    await bot.edit_message_text(
        chat_id=message_content.get("chat_id"),
        message_id=message_content.get("message_id"),
        text=text,
        parse_mode="html",
        reply_markup=kb,
    )

    await state.update_data(**tut_service.get_fsm_data())
    await state.set_state(StartTutorial.in_progress)
    log.info(f"FSM | state=StartTutorial.in_progress user_id={user_id}")


@router.callback_query(StartTutorial.in_progress, F.data.startswith("tut_ev"))
async def tutorial_event_stats_handler(call: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    """Обрабатывает выбор пользователя на шаге туториала."""
    if not call.from_user or not call.data or not call.message:
        return

    user_id = call.from_user.id
    log.info(f"TutorialStats | event=choice_made user_id={user_id} choice='{call.data}'")
    await call.answer()

    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    char_id = session_context.get("char_id")
    if not isinstance(char_id, int):
        log.warning(f"TutorialStats | status=failed reason='Invalid char_id in FSM' user_id={user_id}")
        await Err.invalid_id(call=call)
        return

    session_dto = SessionDataDTO(**session_context)
    anim_service = UIAnimationService(bot=bot, message_data=session_dto)

    async def run_logic():
        tut_service = TutorialServiceStats(
            char_id=char_id,
            event_pool=state_data.get("event_pool"),
            sim_text_count=state_data.get("sim_text_count", 0),
            bonus_dict=state_data.get("bonus_dict"),
        )
        # Исправление: Проверяем call.data перед передачей в add_bonus
        if call.data:
            tut_service.add_bonus(choice_key=call.data)
        else:
            log.warning(f"TutorialStats | reason='call.data is None, cannot add bonus' user_id={user_id}")
            # Возможно, здесь нужно обработать ошибку или пропустить добавление бонуса
        next_step = tut_service.get_next_step()
        await state.update_data(**tut_service.get_fsm_data())
        return next_step, tut_service

    results = await asyncio.gather(
        anim_service.animate_loading(duration=1.5, text="⚙️ <b>Анализ выбора...</b>"),
        run_logic(),
    )
    next_step_data, tut_service = results[1]

    message_content = session_context.get("message_content")
    if not isinstance(message_content, dict):
        log.error(f"TutorialStats | status=failed reason='message_content not found in FSM' user_id={user_id}")
        await Err.message_content_not_found_in_fsm(call)
        return

    if next_step_data is None:
        log.info(f"TutorialStats | status=finished char_id={char_id}")
        animation_steps, final_kb = tut_service.get_data_animation_steps()
        await anim_service.animate_sequence(sequence=animation_steps, final_kb=final_kb)
        await state.set_state(StartTutorial.confirmation)
        log.info(f"FSM | state=StartTutorial.confirmation user_id={user_id}")
    else:
        text, kb = next_step_data
        log.debug(f"TutorialStats | step=next_render user_id={user_id}")
        await bot.edit_message_text(
            chat_id=message_content.get("chat_id"),
            message_id=message_content.get("message_id"),
            text=text,
            parse_mode="html",
            reply_markup=kb,
        )


@router.callback_query(StartTutorial.confirmation, F.data.startswith("tut:"))
async def tutorial_confirmation_handler(
    call: CallbackQuery, state: FSMContext, bot: Bot, session: AsyncSession
) -> None:
    """Обрабатывает финальный выбор после распределения характеристик."""
    if not call.from_user or not call.data:
        return

    user_id = call.from_user.id
    log.info(f"TutorialConfirm | event=choice_made user_id={user_id} choice='{call.data}'")
    await call.answer()
    start_time = time.monotonic()

    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    char_id = session_context.get("char_id")
    message_content = session_context.get("message_content")

    if not isinstance(char_id, int) or not isinstance(message_content, dict):
        log.warning(f"TutorialConfirm | status=failed reason='Invalid FSM data' user_id={user_id}")
        await Err.invalid_id(call)
        return

    tut_service = TutorialServiceStats(
        char_id=char_id,
        event_pool=state_data.get("event_pool"),
        sim_text_count=state_data.get("sim_text_count", 0),
        bonus_dict=state_data.get("bonus_dict"),
    )

    if call.data == "tut:restart":
        log.info(f"TutorialConfirm | action=restart user_id={user_id} char_id={char_id}")
        await state.set_state(StartTutorial.start)
        await state.update_data(bonus_dict={}, event_pool=None, sim_text_count=0)
        text, kb = tut_service.get_restart_stats()
        await bot.edit_message_text(
            chat_id=message_content.get("chat_id"),
            message_id=message_content.get("message_id"),
            text=text,
            parse_mode="html",
            reply_markup=kb,
        )

    elif call.data == "tut:continue":
        bonus_dict = state_data.get("bonus_dict")
        if not isinstance(bonus_dict, dict):
            log.warning(
                f"TutorialConfirm | action=continue status=failed reason='bonus_dict not found' user_id={user_id}"
            )
            await Err.invalid_id(call)
            return

        await await_min_delay(start_time, min_delay=2.0)

        log.info(f"TutorialConfirm | action=continue user_id={user_id} char_id={char_id} bonuses='{bonus_dict}'")
        text, kb = await tut_service.finalize_stats(session)
        await bot.edit_message_text(
            chat_id=message_content.get("chat_id"),
            message_id=message_content.get("message_id"),
            text=text,
            parse_mode="html",
            reply_markup=kb,
        )
    else:
        log.error(f"TutorialConfirm | status=failed reason='Unknown callback' data='{call.data}' user_id={user_id}")
        await Err.callback_data_missing(call)
