# app/handlers/callback/tutorial/tutorial_game.py
import time
import logging

from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.resources.fsm_states.states import StartTutorial
from app.services.helpers_module.helper_id_callback import error_msg_default
from app.services.ui_service.helpers_ui.ui_tools import animate_message_sequence, await_min_delay
from app.services.ui_service.tutorial.tutorial_service import TutorialService

log = logging.getLogger(__name__)

router = Router(name="tutorial_game_router")


@router.callback_query(StartTutorial.start, F.data.startswith("tut:start"))
async def start_tutorial_handler(call: CallbackQuery, state: FSMContext, bot: Bot):
    """
    Начинает туториал по распределению очков характеристик.

    Этот обработчик запускается после создания персонажа. Он инициализирует
    сервис туториала, отображает первый шаг (вопрос) и переводит FSM
    в состояние прохождения туториала.

    Args:
        call (CallbackQuery): Входящий callback от кнопки начала туториала.
        state (FSMContext): Состояние FSM.
        bot (Bot): Экземпляр бота.

    Returns:
        None
    """
    log.debug("Начало работы start_tutorial_handler")
    await call.answer()

    state_data = await state.get_data()
    char_id = state_data.get("char_id")

    if not char_id:
        log.error("char_id не найден в FSM. Невозможно начать туториал.")
        await state.clear()
        await error_msg_default(call=call)
        return

    # Инициализируем сервис туториала с ID персонажа.
    tut_service = TutorialService(
        char_id=char_id,
        bonus_dict={}
    )

    # Получаем текст и клавиатуру для первого шага.
    text, kb = tut_service.get_next_step()

    message_content = state_data.get("message_content")
    if not message_content:
        log.error("message_content не найден в FSM.")
        await error_msg_default(call=call)
        return

    await bot.edit_message_text(
        chat_id=message_content.get("chat_id"),
        message_id=message_content.get("message_id"),
        text=text,
        parse_mode="html",
        reply_markup=kb
    )

    # Сохраняем данные туториала (пул событий, бонусы) в FSM.
    await state.update_data(**tut_service.get_fsm_data())
    await state.set_state(StartTutorial.in_progress)
    log.debug(f"Состояние state в конце start_tutorial_handler = {await state.get_data()}")


@router.callback_query(StartTutorial.in_progress, F.data.startswith("tut_ev"))
async def tutorial_event_stats_handler(call: CallbackQuery, state: FSMContext, bot: Bot):
    """
    Обрабатывает выбор пользователя на одном из шагов туториала.

    Эта функция является основным циклом распределения очков. Она получает
    ответ пользователя, добавляет соответствующий бонус к характеристикам,
    и отображает следующий шаг. Если шаги закончились, запускает
    анимацию подсчета результатов.

    Args:
        call (CallbackQuery): Входящий callback с выбором пользователя (e.g., "tut_ev:strength").
        state (FSMContext): Состояние FSM.
        bot (Bot): Экземпляр бота.

    Returns:
        None
    """
    await call.answer()
    start_time = time.monotonic()
    state_data = await state.get_data()

    # Воссоздаем сервис из данных FSM, чтобы продолжить с того же места.
    tut_service = TutorialService(
        char_id=state_data.get("char_id"),
        event_pool=state_data.get("event_pool"),
        sim_text_count=state_data.get("sim_text_count", 0),
        bonus_dict=state_data.get("bonus_dict")
    )

    choice = call.data
    if not choice:
        log.error("Отсутствует callback.data в tutorial_event_stats_handler")
        await error_msg_default(call=call)
        return

    # Добавляем бонус на основе выбора пользователя.
    tut_service.add_bonus(choice_key=choice)

    # Получаем следующий шаг или None, если шаги закончились.
    text, kb = tut_service.get_next_step()

    message_content = state_data.get("message_content")
    if not message_content:
        await error_msg_default(call)
        return

    # Сохраняем обновленные данные туториала (оставшиеся события, бонусы).
    await state.update_data(**tut_service.get_fsm_data())

    # Если text is None, значит, туториал завершен.
    if text is None:
        # Готовим данные для финальной анимации.
        animation_steps, final_kb = tut_service.get_data_animation_steps()

        # Запускаем анимацию подсчета очков.
        await animate_message_sequence(
            message_to_edit=message_content,
            sequence=animation_steps,
            bot=bot,
            final_reply_markup=final_kb
        )
        # Переводим FSM в состояние подтверждения.
        await state.set_state(StartTutorial.confirmation)
    else:
        # Если есть следующий шаг, просто обновляем сообщение.
        if start_time:
            await await_min_delay(start_time, min_delay=0.3)

        await bot.edit_message_text(
            chat_id=message_content.get("chat_id"),
            message_id=message_content.get("message_id"),
            text=text,
            parse_mode="html",
            reply_markup=kb
        )


@router.callback_query(StartTutorial.confirmation, F.data.startswith("tut:"))
async def tutorial_confirmation_handler(call: CallbackQuery, state: FSMContext, bot: Bot):
    """
    Обрабатывает финальный выбор после распределения характеристик.

    Пользователь может подтвердить характеристики, начать заново или
    (в будущем) завершить создание.

    Args:
        call (CallbackQuery): Входящий callback (tut:restart, tut:continue, tut:finish).
        state (FSMContext): Состояние FSM.
        bot (Bot): Экземпляр бота.

    Returns:
        None
    """
    await call.answer()
    start_time = time.monotonic()
    state_data = await state.get_data()
    call_data = call.data

    if not state_data:
        await error_msg_default(call)
        return

    char_id = state_data.get("char_id")
    message_content = state_data.get("message_content")

    if not message_content:
        await error_msg_default(call)
        return

    # Воссоздаем сервис с текущими данными для выполнения действий.
    tut_service = TutorialService(
        char_id=char_id,
        event_pool=state_data.get("event_pool"),
        sim_text_count=state_data.get("sim_text_count", 0),
        bonus_dict=state_data.get("bonus_dict")
    )

    if call_data == "tut:restart":
        # Сбрасываем состояние туториала для повторного прохождения.
        await state.set_state(StartTutorial.start)
        # Очищаем только данные туториала, сохраняя char_id.
        await state.update_data(tut_service={}, bonus_dict={}, event_pool=None, sim_text_count=0)

        text, kb = tut_service.get_restart_stats()

        if start_time:
            await await_min_delay(start_time, min_delay=0.3)

        await bot.edit_message_text(
            chat_id=message_content.get("chat_id"),
            message_id=message_content.get("message_id"),
            text=text,
            parse_mode="html",
            reply_markup=kb
        )

    elif call_data == "tut:continue":
        # Применяем бонусы к характеристикам персонажа в базе данных.
        if not char_id or not state_data.get("bonus_dict"):
            await error_msg_default(call)
            return

        text, kb = await tut_service.update_stats_und_get()

        if start_time:
            await await_min_delay(start_time, min_delay=0.3)

        await bot.edit_message_text(
            chat_id=message_content.get("chat_id"),
            message_id=message_content.get("message_id"),
            text=text,
            parse_mode="html",
            reply_markup=kb
        )
        # Здесь можно установить следующий стейт, например, завершение туториала
        # await state.set_state(SomeOtherState.next_step)

    elif call_data == "tut:finish":
        # TODO: Реализовать логику завершения туториала и перехода в игру.
        await state.clear()
        await state.update_data(char_id=char_id)
        await call.message.edit_text("Дальше пока не разработано.")
    else:
        # Обработка непредусмотренных callback'ов.
        await state.clear()
        await state.update_data(char_id=char_id)
        await call.message.edit_text("Произошла ошибка. Дальше пока не разработано.")
