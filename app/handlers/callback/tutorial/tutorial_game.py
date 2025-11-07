# app/handlers/fsn_callback/tutorial_game.py
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

router = Router(name="character_creation_fsm")



@router.callback_query(StartTutorial.start, F.data.startswith("tut:start"))
async def start_tutorial_handler(call: CallbackQuery, state: FSMContext,bot: Bot):
    """
        Старт tutorial.
    """
    log.debug("начало работы ")
    await call.answer()


    state_data = await state.get_data()
    char_id = state_data.get("char_id")

    if not char_id:
        await state.clear()
        await error_msg_default(call=call)

    tut_service = TutorialService(
        char_id=char_id,
        bonus_dict= {}
    )

    text, kb = tut_service.get_next_step()

    message_content = state_data.get("message_content")

    if message_content:
        await bot.edit_message_text(
            chat_id=message_content.get("chat_id"),
            message_id=message_content.get("message_id"),
            text=text,
            parse_mode="html",
            reply_markup=kb
        )
    else:
        await error_msg_default(call=call)

    await state.update_data(tut_service=tut_service.get_fsm_data())
    await state.set_state(StartTutorial.in_progress)



@router.callback_query(StartTutorial.in_progress, F.data.startswith("tut_ev"))
async def tutorial_event_stats_handler(call: CallbackQuery, state: FSMContext, bot: Bot):
    """
    основной цикл прохождения формирования Stats персонажа.

    """
    await call.answer()
    start_time = time.monotonic()
    state_data = await state.get_data()

    # 1. VVV Вот как ты получишь свои данные VVV
    tut_data = state_data.get("tut_service", {})

    tut_service = TutorialService(
        char_id=tut_data.get("char_id"),
        event_pool=tut_data.get("event_pool"),
        sim_text_count=tut_data.get("sim_text_count", 0),
        bonus_dict=tut_data.get("bonus_dict")
    )

    choice = call.data

    if not choice:
        log.debug(f"нету каллбека статов")
        await error_msg_default(call=call)


    tut_service.add_bonus(choice_key=choice)

    text, kb = tut_service.get_next_step()

    message_content = state_data.get("message_content")

    if not message_content:
        await error_msg_default(call)  # На всякий случай
        return

    await state.update_data(tut_service=tut_service.get_fsm_data())

    if text is None:

        # 1. Готовим данные для анимации
        step, kb = tut_service.get_data_animation_steps()

        # 2. отправляем сообщения
        await animate_message_sequence(
            message_to_edit=message_content,
            sequence=step,
            bot=bot,
            final_reply_markup=kb
        )

        # 4. Меняем стейт (хелпер уже отработал)
        await state.set_state(StartTutorial.confirmation)

    else:

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
    Финальный обработчик генерации персонажа.

    """
    await call.answer()
    start_time = time.monotonic()
    state_data = await state.get_data()
    call_data = call.data

    # 1. VVV Вот как ты получишь свои данные VVV
    tut_data = state_data.get("tut_service", {})

    if tut_data:
        char_id = tut_data.get("char_id")

        tut_service = TutorialService(
            char_id=char_id,
            event_pool=tut_data.get("event_pool"),
            sim_text_count=tut_data.get("sim_text_count", 0),
            bonus_dict=tut_data.get("bonus_dict")
        )

        message_content = state_data.get("message_content")

        if call_data == "tut:restart":

            await state.set_state(StartTutorial.start)
            await state.update_data(tut_service={}, char_id=char_id)

            text, kb = tut_service.get_restart_stats()

            if not message_content:
                await error_msg_default(call)

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

            if not char_id or not tut_data.get("bonus_dict"):
                await error_msg_default(call)

            text, kb = await tut_service.update_stats_und_get()

            if not message_content:
                await error_msg_default(call)

            if start_time:
                await await_min_delay(start_time, min_delay=0.3)

            await bot.edit_message_text(
                chat_id=message_content.get("chat_id"),
                message_id=message_content.get("message_id"),
                text=text,
                parse_mode="html",
                reply_markup=kb
            )

        elif call_data == "tut:finish":
            # TODO: доделать
            await state.clear()
            await state.update_data(char_id=char_id)
            await call.message.edit_text(
                """
                Дальше пока не разработано. 
                
                """)
        else:
            # TODO: доделать
            await state.clear()
            await state.update_data(char_id=char_id)
            await call.message.edit_text(
                """
                Дальше пока не разработано. 
    
                """)





