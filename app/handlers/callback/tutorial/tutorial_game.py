# app/handlers/callback/tutorial/tutorial_game.py
import time
import logging

from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.resources.fsm_states.states import StartTutorial
from app.services.helpers_module.callback_exceptions import UIErrorHandler as ERR
from app.services.ui_service.helpers_ui.ui_tools import animate_message_sequence, await_min_delay
from app.services.ui_service.tutorial.tutorial_service import TutorialService

log = logging.getLogger(__name__)

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
    char_id = state_data.get("char_id")
    log.info(f"Хэндлер 'start_tutorial_handler' [tut:start] вызван user_id={user_id}, char_id={char_id}")
    await call.answer()

    if not char_id:
        log.warning(f"User {user_id} в 'start_tutorial_handler' имел 'char_id=None'. Отправка ошибки.")
        await ERR.invalid_id(call=call)
        return

    tut_service = TutorialService(char_id=char_id, bonus_dict={})

    text, kb = tut_service.get_next_step()
    log.debug(f"Для user_id={user_id} получен первый шаг туториала.")

    message_content = state_data.get("message_content")
    if not message_content:
        log.error(f"Не найден 'message_content' в FSM для user_id={user_id}.")
        await ERR.message_content_not_found_in_fsm(call=call)
        return

    await bot.edit_message_text(
        chat_id=message_content.get("chat_id"),
        message_id=message_content.get("message_id"),
        text=text,
        parse_mode="html",
        reply_markup=kb
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
    if not call.from_user:
        log.warning("Хэндлер 'tutorial_event_stats_handler' получил обновление без 'from_user'.")
        return

    choice = call.data
    user_id = call.from_user.id
    log.info(f"Хэндлер 'tutorial_event_stats_handler' [{choice}] вызван user_id={user_id}")
    await call.answer()
    start_time = time.monotonic()

    state_data = await state.get_data()
    char_id = state_data.get("char_id")
    if not char_id:
        log.warning(f"User {user_id} в 'tutorial_event_stats_handler' имел 'char_id=None'.")
        await ERR.invalid_id(call=call)
        return

    # Воссоздаем сервис из FSM.
    tut_service = TutorialService(
        char_id=char_id,
        event_pool=state_data.get("event_pool"),
        sim_text_count=state_data.get("sim_text_count", 0),
        bonus_dict=state_data.get("bonus_dict")
    )
    log.debug(f"Сервис туториала для user_id={user_id} воссоздан из FSM.")

    tut_service.add_bonus(choice_key=choice)
    log.debug(f"Бонус '{choice}' добавлен для char_id={char_id}. Текущие бонусы: {tut_service.bonus_dict}")

    # 1. Сначала получаем результат в ОДНУ переменную
    next_step_data = tut_service.get_next_step()

    # 2. Получаем message_content (это можно сделать до проверки)
    message_content = state_data.get("message_content")
    if not message_content:
        log.error(f"Не найден 'message_content' в FSM для user_id={user_id}.")
        await ERR.message_content_not_found_in_fsm(call)
        return

    # 3. Обновляем FSM (тоже можно сделать до проверки)
    await state.update_data(**tut_service.get_fsm_data())
    log.debug(f"Данные FSM для user_id={user_id} обновлены.")

    # 4. Теперь ПРОВЕРЯЕМ, не None ли результат
    if next_step_data is None:
        log.info(f"Туториал для char_id={char_id} завершен. Запуск анимации подсчета.")
        animation_steps, final_kb = tut_service.get_data_animation_steps()
        await animate_message_sequence(
            message_to_edit=message_content,
            sequence=animation_steps,
            bot=bot,
            final_reply_markup=final_kb
        )
        await state.set_state(StartTutorial.confirmation)
        log.info(f"FSM для user_id={user_id} переведен в состояние 'StartTutorial.confirmation'.")
    else:
        # 5. И ТОЛЬКО ЕСЛИ НЕ None, мы его распаковываем
        text, kb = next_step_data

        log.debug(f"Отображение следующего шага туториала для char_id={char_id}.")
        await await_min_delay(start_time, min_delay=0.3)
        await bot.edit_message_text(
            chat_id=message_content.get("chat_id"),
            message_id=message_content.get("message_id"),
            text=text,
            parse_mode="html",
            reply_markup=kb
        )

@router.callback_query(StartTutorial.confirmation, F.data.startswith("tut:"))
async def tutorial_confirmation_handler(call: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    """
    Обрабатывает финальный выбор после распределения характеристик.

    Args:
        call (CallbackQuery): Callback (tut:restart, tut:continue, tut:finish).
        state (FSMContext): Состояние FSM.
        bot (Bot): Экземпляр бота.

    Returns:
        None
    """
    if not call.from_user:
        log.warning("Хэндлер 'tutorial_confirmation_handler' получил обновление без 'from_user'.")
        return

    call_data = call.data
    user_id = call.from_user.id
    log.info(f"Хэндлер 'tutorial_confirmation_handler' [{call_data}] вызван user_id={user_id}")
    await call.answer()
    start_time = time.monotonic()

    state_data = await state.get_data()
    char_id = state_data.get("char_id")
    message_content = state_data.get("message_content")

    if not all([char_id, message_content]):
        log.warning(f"Недостаточно данных в FSM для user_id={user_id} в 'tutorial_confirmation_handler'.")
        await ERR.invalid_id(call)
        return

    tut_service = TutorialService(
        char_id=char_id,
        event_pool=state_data.get("event_pool"),
        sim_text_count=state_data.get("sim_text_count", 0),
        bonus_dict=state_data.get("bonus_dict")
    )
    log.debug(f"Сервис туториала для user_id={user_id} воссоздан из FSM.")

    await await_min_delay(start_time, min_delay=0.3)

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
            reply_markup=kb
        )
        log.debug(f"Сообщение о рестарте отправлено user_id={user_id}.")

    elif call_data == "tut:continue":
        bonus_dict = state_data.get("bonus_dict")
        if not bonus_dict:
            log.warning(f"User {user_id} попытался продолжить туториал без бонусов.")
            await ERR.invalid_id(call)
            return

        log.info(f"Пользователь {user_id} подтвердил характеристики для char_id={char_id}. Бонусы: {bonus_dict}")
        text, kb = await tut_service.update_stats_und_get()
        await bot.edit_message_text(
            chat_id=message_content.get("chat_id"),
            message_id=message_content.get("message_id"),
            text=text,
            parse_mode="html",
            reply_markup=kb
        )
        log.debug(f"Сообщение с финальными статами отправлено user_id={user_id}.")
        # TODO: Установить следующий стейт, например, завершение туториала
        # await state.set_state(SomeOtherState.next_step)

    elif call_data == "tut:finish":
        log.info(f"Пользователь {user_id} нажал 'Завершить' (заглушка) для char_id={char_id}.")
        await state.clear()
        await state.update_data(char_id=char_id)
        await call.message.edit_text("Дальше пока не разработано.")
    else:
        log.error(f"Неизвестный callback '{call_data}' в 'tutorial_confirmation_handler' от user_id={user_id}.")
        await ERR.callback_data_missing(call)
