# app/handlers/callback/tutorial/tutorial_skill.py
import logging
import time
from typing import Dict, Any, Optional

from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.resources.fsm_states.states import StartTutorial, CharacterLobby
from app.resources.keyboards.callback_data import TutorialQuestCallback
from app.resources.texts.ui_messages import TEXT_AWAIT
from app.services.helpers_module.DTO_helper import fsm_clean_core_state
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


@router.callback_query(
    StartTutorial.skill_confirm,  # 1. Ловим состояние, в которое нас привел предыдущий шаг
    TutorialQuestCallback.filter(F.phase == "p_end")  # 2. Ловим ТОЛЬКО кнопки финала
)
async def skill_confirm_handler(
        call: CallbackQuery,
        state: FSMContext,
        callback_data: TutorialQuestCallback,
        bot: Bot,
) -> None:
    """
    Обрабатывает финальный выбор в туториале по навыкам (выбор профессии/лута).

    Этот хэндлер:
    1. Сохраняет финальный выбор.
    2. Вызывает сервис для "финализации" навыков (разблокировка в БД,
       смена game_stage).
    3. Обновляет UI на финальное сообщение "пробуждения".
    4. Очищает FSM от данных туториала.
    5. Переводит игрока в состояние лобби.
    """
    if not call.from_user:
        log.warning("Handler 'skill_confirm_handler' received update without 'from_user'.")
        return
    start_time = time.monotonic()

    await call.message.edit_text(
        text=TEXT_AWAIT,
        parse_mode="html",
        reply_markup=None
    )

    # --- 1. Сбор данных ---
    final_choice = callback_data.value
    user_id = call.from_user.id

    state_data = await state.get_data()
    char_id = state_data.get("char_id")
    skill_choices_list: list = state_data.get("skill_choices_list", [])
    message_content: Optional[Dict[str, Any]] = state_data.get("message_content")

    log.info(
        f"Хэндлер 'skill_confirm_handler' [p_end:{final_choice}] вызван user_id={user_id}, char_id={char_id}"
    )
    await call.answer()

    # --- 2. Валидация ---
    if not char_id or not message_content:
        log.error(f"User {user_id}: 'char_id' или 'message_content' не найдены в FSM для skill_confirm_handler.")
        await ERR.generic_error(call=call)
        return

    if final_choice:
        skill_choices_list.append(final_choice)

    log.debug(f"Финальный список выбора навыков для char_id={char_id}: {skill_choices_list}")

    # --- 3. Подготовка UI и Сервиса ---
    # Инициализируем сервис с финальным списком навыков
    tut_service = TutorialServiceSkills(skills_db=skill_choices_list)

    # Заранее готовим UI (текст и кнопку "Открыть глаза")
    text, kb = tut_service.get_awakening_data(char_id=char_id, final_choice_key=final_choice)

    # --- 4. Финализация (БД, UI, FSM) ---
    # Все критические операции в ОДНОМ блоке try...except
    try:
        # Шаг 1: Работа с Базой Данных
        await tut_service.finalize_skill_selection(char_id=char_id)
        log.info(f"DB-операции для char_id={char_id} (навыки, game_stage) успешно завершены.")

        # Задержка перед обновлением UI
        await await_min_delay(start_time, min_delay=0.8)

        # Шаг 2: Обновление UI (Только после успеха БД)
        await bot.edit_message_text(
            chat_id=message_content["chat_id"],
            message_id=message_content["message_id"],
            text=text,
            parse_mode="html",
            reply_markup=kb
        )
        log.debug(f"UI для user_id={user_id} обновлено на 'awakening_data'.")

        # Шаг 3: Очистка FSM
        await fsm_clean_core_state(
            state=state,
            event_source=call
        )
        log.debug(f"FSM state для user_id={user_id} очищен.")

        # Шаг 4: Смена стейта FSM
        await state.set_state(CharacterLobby.selection)
        log.info(f"User {user_id} завершил туториал. FSM переведен в CharacterLobby.selection.")

    except Exception as e:
        # Если упадет *любой* из 4-х шагов, мы попадем сюда
        log.exception(f"Критический сбой при финализации туториала для user_id={user_id}: {e}")
        await ERR.generic_error(call=call)