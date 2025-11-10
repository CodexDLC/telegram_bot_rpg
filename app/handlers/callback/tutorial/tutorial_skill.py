# app/handlers/callback/tutorial/tutorial_skill.py
import logging
import time
from typing import Dict, Any, Optional

from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.resources.fsm_states.states import StartTutorial
from app.resources.keyboards.callback_data import TutorialQuestCallback
from app.services.ui_service.helpers_ui.ui_tools import await_min_delay, animate_message_sequence
from app.services.ui_service.tutorial.tutorial_service_skill import TutorialServiceSkills
from app.services.helpers_module.callback_exceptions import UIErrorHandler as ERR

log = logging.getLogger(__name__)

router = Router(name="tutorial_skill_router")


@router.callback_query(StartTutorial.confirmation, F.data == "tut_quest:start_skill_phase")
async def start_skill_phase_handler(call: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    """
    Обрабатывает начало фазы выбора навыков в туториале.

    Этот хэндлер запускается, когда пользователь нажимает кнопку,
    соответствующую началу выбора навыков. Он инициализирует
    сервис туториала и отображает первый шаг квеста.

    Args:
        call: Объект CallbackQuery, инициировавший вызов.
        state: Контекст состояния FSM для управления состоянием пользователя.
        bot: Экземпляр бота для взаимодействия с API Telegram.
    """
    if not call.from_user:
        log.warning("Handler 'start_skill_phase_handler' received update without 'from_user'.")
        return

    start_time = time.monotonic()
    log.debug(f"User {call.from_user.id} started skill phase.")

    state_data = await state.get_data()
    message_content: Optional[Dict[str, Any]] = state_data.get("message_content")

    # Проверка наличия message_content в состоянии FSM
    if not message_content or "chat_id" not in message_content or "message_id" not in message_content:
        log.error(f"User {call.from_user.id}: 'message_content' not found or incomplete in FSM state.")
        await ERR.message_content_not_found_in_fsm(call=call)
        return

    # Инициализируем сервис с пустым списком для сбора навыков
    skill_choices_list = []
    await state.update_data(skill_choices_list=skill_choices_list)

    tut_service = TutorialServiceSkills(skills_db=skill_choices_list)
    text, kb = tut_service.get_start_data()

    await await_min_delay(start_time, min_delay=0.8)

    await bot.edit_message_text(
        chat_id=message_content["chat_id"],
        message_id=message_content["message_id"],
        text=text,
        parse_mode="html",
        reply_markup=kb
    )

    await state.set_state(StartTutorial.in_skills_progres)
    log.debug(f"User {call.from_user.id} moved to state StartTutorial.in_skills_progres.")


@router.callback_query(StartTutorial.in_skills_progres, TutorialQuestCallback.filter())
async def in_skills_progres_handler(
        call: CallbackQuery,
        state: FSMContext,
        callback_data: TutorialQuestCallback,
        bot: Bot,
) -> None:
    """
    Обрабатывает шаги пользователя в процессе выбора навыков.

    Этот хэндлер вызывается на каждом шаге квеста выбора навыков.
    Он использует TutorialServiceSkills для получения следующего шага,
    обновляет сообщение и сохраняет выбор пользователя.

    Args:
        call: Объект CallbackQuery от пользователя.
        state: Контекст состояния FSM.
        callback_data: Распарсенные данные из callback-кнопки.
        bot: Экземпляр бота.
    """
    if not call.from_user:
        log.warning("Handler 'in_skills_progres_handler' received update without 'from_user'.")
        return

    start_time = time.monotonic()
    log.debug(
        f"User {call.from_user.id} in skill progress. "
        f"Callback data: phase='{callback_data.phase}', branch='{callback_data.branch}', value='{callback_data.value}'"
    )

    state_data = await state.get_data()
    message_content: Optional[Dict[str, Any]] = state_data.get("message_content")
    skill_choices_list: list = state_data.get("skill_choices_list", [])

    # Проверка наличия message_content
    if not message_content or "chat_id" not in message_content or "message_id" not in message_content:
        log.error(f"User {call.from_user.id}: 'message_content' not found or incomplete in FSM state.")
        await ERR.message_content_not_found_in_fsm(call=call)
        return

    try:
        tut_service = TutorialServiceSkills(callback_data=callback_data, skills_db=skill_choices_list)
        text, kb = tut_service.get_next_data()
    except ValueError as e:
        log.error(f"User {call.from_user.id}: Error getting next tutorial step. Details: {e}")
        await call.answer("Произошла ошибка при обработке вашего выбора. Попробуйте снова.", show_alert=True)
        return

    # Обработка и отправка ответа в зависимости от типа контента
    if isinstance(text, str):
        await await_min_delay(start_time, min_delay=0.8)
        await bot.edit_message_text(
            chat_id=message_content["chat_id"],
            message_id=message_content["message_id"],
            text=text,
            parse_mode="html",
            reply_markup=kb
        )
    elif isinstance(text, list):
        # Дополнительная проверка на корректность формата для анимации
        if all(isinstance(item, tuple) and len(item) == 2 for item in text):
            await await_min_delay(start_time, min_delay=0.8)
            await animate_message_sequence(
                message_to_edit=message_content,
                sequence=tuple(text),
                bot=bot,
                final_reply_markup=kb
            )
        else:
            log.error(f"User {call.from_user.id}: Invalid format for message animation sequence. Data: {text}")
            await ERR.message_content_not_found_in_fsm(call=call) # Можно заменить на более специфичную ошибку
            return
    else:
        log.error(f"User {call.from_user.id}: Received unexpected data type from service: {type(text)}")
        await ERR.message_content_not_found_in_fsm(call=call) # Аналогично, нужна более специфичная ошибка
        return

    # Обновление списка выбранных навыков в FSM
    updated_skills = tut_service.get_skills_db()
    await state.update_data(skill_choices_list=updated_skills)
    log.debug(f"User {call.from_user.id} updated skills: {updated_skills}")

    # Переход в следующее состояние, если это финальный шаг
    if callback_data.phase == "finale":
        await state.set_state(StartTutorial.skill_confirm)
        log.debug(f"User {call.from_user.id} moved to state StartTutorial.skill_confirm.")
