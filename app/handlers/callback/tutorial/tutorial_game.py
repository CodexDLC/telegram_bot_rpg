# app/handlers/callback/tutorial/tutorial_game.py
import asyncio
import time
from typing import Any

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from app.resources.fsm_states.states import StartTutorial
from app.resources.schemas_dto.fsm_state_dto import SessionDataDTO
from app.services.helpers_module.callback_exceptions import UIErrorHandler as Err
from app.services.helpers_module.dto_helper import FSM_CONTEXT_KEY
from app.services.ui_service.helpers_ui.ui_animation_service import UIAnimationService
from app.services.ui_service.helpers_ui.ui_tools import await_min_delay
from app.services.ui_service.tutorial.tutorial_service import TutorialServiceStats

router = Router(name="tutorial_game_router")


@router.callback_query(StartTutorial.start, F.data.startswith("tut:start"))
async def start_tutorial_handler(call: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    """
    Начинает туториал по распределению очков характеристик.

    Args:
        call (CallbackQuery): Callback от кнопки начала туториала.
        state (FSMContext): Состояние FSM.
        bot (Bot): Экземпляр бота.

    Returns:
        None
    """
    if not call.from_user:
        log.warning("Хэндлер 'start_tutorial_handler' получил обновление без 'from_user'.")
        return

    user_id = call.from_user.id
    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    char_id = session_context.get("char_id")
    log.info(f"Хэндлер 'start_tutorial_handler' [tut:start] вызван user_id={user_id}, char_id={char_id}")
    await call.answer()

    if not isinstance(char_id, int):
        log.warning(f"User {user_id} в 'start_tutorial_handler' имел 'char_id=None' или неверный тип. Отправка ошибки.")
        await Err.invalid_id(call=call)
        return

    tut_service = TutorialServiceStats(char_id=char_id, bonus_dict={})

    next_step_data = tut_service.get_next_step()
    if next_step_data is None:
        log.error("get_next_step() вернул None на первом шаге туториала.")
        await Err.callback_data_missing(call)  # Или другая подходящая ошибка
        return
    text, kb = next_step_data
    log.debug(f"Для user_id={user_id} получен первый шаг туториала.")

    message_content = session_context.get("message_content")
    if not isinstance(message_content, dict):
        log.error(f"Не найден 'message_content' в FSM для user_id={user_id}.")
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
    log.info(f"FSM для user_id={user_id} переведен в состояние 'StartTutorial.in_progress'.")
    log.debug(f"Данные FSM в конце 'start_tutorial_handler': {await state.get_data()}")


@router.callback_query(StartTutorial.in_progress, F.data.startswith("tut_ev"))
async def tutorial_event_stats_handler(call: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    """
    Обрабатывает выбор пользователя на шаге туториала.

    Args:
        call (CallbackQuery): Callback с выбором (e.g., "tut_ev:strength").
        state (FSMContext): Состояние FSM.
        bot (Bot): Экземпляр бота.

    Returns:
        None
    """
    if not call.from_user or not call.data or not call.message:
        log.warning("Хэндлер 'tutorial_event_stats_handler' получил обновление без 'from_user', 'data' или 'message'.")
        return

    choice = call.data
    user_id = call.from_user.id
    log.info(f"Хэндлер 'tutorial_event_stats_handler' [{choice}] вызван user_id={user_id}")
    await call.answer()

    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    char_id = session_context.get("char_id")
    if not isinstance(char_id, int):
        log.warning(f"User {user_id} в 'tutorial_event_stats_handler' имел 'char_id=None' или неверный тип.")
        await Err.invalid_id(call=call)
        return

    # --- Анимация и логика ---
    session_dto = SessionDataDTO(**session_context)
    anim_service = UIAnimationService(bot=bot, message_data=session_dto)

    # Определяем асинхронную под-задачу для логики, чтобы запустить параллельно с анимацией
    async def run_logic():
        tut_service = TutorialServiceStats(
            char_id=char_id,
            event_pool=state_data.get("event_pool"),
            sim_text_count=state_data.get("sim_text_count", 0),
            bonus_dict=state_data.get("bonus_dict"),
        )
        tut_service.add_bonus(choice_key=choice)
        next_step = tut_service.get_next_step()
        await state.update_data(**tut_service.get_fsm_data())
        return next_step, tut_service

    # Запускаем анимацию и логику параллельно и ждем, пока ОБЕ завершатся.
    # `gather` дождется окончания самой долгой задачи, в нашем случае - анимации.
    results = await asyncio.gather(
        anim_service.animate_loading(duration=1.5, text="⚙️ <b>Анализ выбора...</b>"),
        run_logic(),
    )

    # Извлекаем результат из задачи с логикой
    next_step_data, tut_service = results[1]

    message_content = session_context.get("message_content")
    if not isinstance(message_content, dict):
        log.error(f"Не найден 'message_content' в FSM для user_id={user_id}.")
        await Err.message_content_not_found_in_fsm(call)
        return

    # Теперь, после завершения анимации, решаем, что показать
    if next_step_data is None:
        log.info(f"Туториал для char_id={char_id} завершен. Запуск анимации подсчета.")
        animation_steps, final_kb = tut_service.get_data_animation_steps()
        await anim_service.animate_sequence(sequence=animation_steps, final_kb=final_kb)
        await state.set_state(StartTutorial.confirmation)
        log.info(f"FSM для user_id={user_id} переведен в состояние 'StartTutorial.confirmation'.")
    else:
        text, kb = next_step_data
        log.debug(f"Отображение следующего шага туториала для char_id={char_id}.")
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
    """
    Обрабатывает финальный выбор после распределения характеристик.

    Args:
        call (CallbackQuery): Callback (tut:restart, tut:continue, tut:finish).
        state (FSMContext): Состояние FSM.
        bot (Bot): Экземпляр бота.

    Returns:
        None
    """
    if not call.from_user or not call.data:
        log.warning("Хэндлер 'tutorial_confirmation_handler' получил обновление без 'from_user' или 'data'.")
        return

    call_data = call.data
    user_id = call.from_user.id
    log.info(f"Хэндлер 'tutorial_confirmation_handler' [{call_data}] вызван user_id={user_id}")
    await call.answer()
    start_time = time.monotonic()

    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    char_id = session_context.get("char_id")
    message_content: dict[str, Any] | None = session_context.get("message_content")

    if not isinstance(char_id, int) or not isinstance(message_content, dict):
        log.warning(f"Недостаточно данных в FSM для user_id={user_id} в 'tutorial_confirmation_handler'.")
        await Err.invalid_id(call)
        return

    tut_service = TutorialServiceStats(
        char_id=char_id,
        event_pool=state_data.get("event_pool"),
        sim_text_count=state_data.get("sim_text_count", 0),
        bonus_dict=state_data.get("bonus_dict"),
    )
    log.debug(f"Сервис туториала для user_id={user_id} воссоздан из FSM.")

    if call_data == "tut:restart":
        log.info(f"Пользователь {user_id} перезапускает туториал для char_id={char_id}.")
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
        log.debug(f"Сообщение о рестарте отправлено user_id={user_id}.")

    elif call_data == "tut:continue":
        bonus_dict = state_data.get("bonus_dict")
        if not isinstance(bonus_dict, dict):
            log.warning(f"User {user_id} попытался продолжить туториал без бонусов.")
            await Err.invalid_id(call)
            return

        # Добавляем задержку, чтобы пользователь успел прочитать финальный кадр анимации
        await await_min_delay(start_time, min_delay=2.0)

        log.info(f"Пользователь {user_id} подтвердил характеристики для char_id={char_id}. Бонусы: {bonus_dict}")
        text, kb = await tut_service.finalize_stats(session)
        await bot.edit_message_text(
            chat_id=message_content.get("chat_id"),
            message_id=message_content.get("message_id"),
            text=text,
            parse_mode="html",
            reply_markup=kb,
        )
        log.debug(f"Сообщение с финальными статами отправлено user_id={user_id}.")

    else:
        log.error(f"Неизвестный callback '{call_data}' в 'tutorial_confirmation_handler' от user_id={user_id}.")
        await Err.callback_data_missing(call)
