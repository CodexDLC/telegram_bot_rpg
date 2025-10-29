# app/handlers/fsn_callback/tutorial_game.py
import asyncio
import logging
from aiogram import Router, F

from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message


from app.resources.fsm_states.states import StartTutorial
from app.resources.keyboards.inline_kb.loggin_und_new_character import tutorial_kb
from app.resources.texts.game_messages.tutorial_messages import TutorialMessages
from app.services.helpers_module.tutorial_utils import prepare_tutorial_step, summ_stat_bonus
from database.db import get_db_connection
from database.repositories import get_character_stats_repo

log = logging.getLogger(__name__)

router = Router(name="character_creation_fsm")



@router.callback_query(StartTutorial.start, F.data.startswith("tut:start"))
async def start_tutorial_handler(call: CallbackQuery, state: FSMContext):
    """
        Старт tutorial.
    """
    await call.answer()

    state_data = await state.get_data()
    char_id = state_data.get("character_id")
    sim_text_count = 0
    event_pool = []


    if not char_id:
        await state.clear()
        return await call.message.edit_text(
            f"⚠️ Ошибка: Данные создания утеряны. Начните заново цепочку создания персонажа")

    text, kb, sim_text_count, event_pool = prepare_tutorial_step(event_pool,sim_text_count)

    log.info(f" Мы видим текс который вернулся {text} ")

    await state.update_data(
        char_id=char_id,
        event_pool=event_pool,
        sim_text_count=sim_text_count,
        bonus_dict= {})

    await state.set_state(StartTutorial.in_progress)

    if isinstance(call.message, Message):
        await call.message.edit_text(text, parse_mode='HTML', reply_markup=kb)

    return None

@router.callback_query(StartTutorial.in_progress, F.data.startswith("tut_ev"))
async def tutorial_event_stats_handler(call: CallbackQuery, state: FSMContext):
    """
    основной цикл прохождения формирования Stats персонажа.

    """
    await call.answer()
    choice = call.data
    state_data = await state.get_data()
    event_pool = state_data.get("event_pool")
    sim_text_count = state_data.get("sim_text_count")
    bonus_dict = state_data.get("bonus_dict")
    char_id = state_data.get("character_id")

    if not choice:
        return await call.message.edit_text(
            f"⚠️ Ошибка: Данные создания утеряны. Начните заново цепочку создания персонажа")

    bonus_dict = summ_stat_bonus(key=choice, bonus_dict=bonus_dict)

    text, kb, sim_text_count, event_pool = prepare_tutorial_step(event_pool, sim_text_count)

    await state.update_data(
        char_id=char_id,
        event_pool=event_pool,
        sim_text_count=sim_text_count,
        bonus_dict=bonus_dict
    )

    if text is None:

        await state.update_data(bonus_dict=bonus_dict)  # Сохраняем финальные бонусы

        message_to_edit = None
        animation_steps = TutorialMessages.TUTORIAL_ANALYSIS_TEXT
        total_steps = len(animation_steps)

        for i, (text_line, pause_duration) in enumerate(animation_steps):

            is_last_step = (i == total_steps - 1)

            reply_markup = None
            if is_last_step:
                reply_markup = tutorial_kb(TutorialMessages.TUTORIAL_ANALYSIS_BUTTON)

            # Редактируем сообщение
            if message_to_edit is None:
                message_to_edit = await call.message.edit_text(
                    text_line,
                    parse_mode='HTML',
                    reply_markup=reply_markup
                )
            else:
                await call.message.edit_text(
                    text_line,
                    parse_mode='HTML',
                    reply_markup=reply_markup
                )

            # Если это был последний шаг, меняем стейт (как ты и хотел)
            if is_last_step:
                await state.set_state(StartTutorial.confirmation)

            await asyncio.sleep(pause_duration)
    else:


        if isinstance(call.message, Message):
            await call.message.edit_text(text, parse_mode='HTML', reply_markup=kb)

    return None


@router.callback_query(StartTutorial.confirmation, F.data.startswith("tut:"))
async def tutorial_confirmation_handler(call: CallbackQuery, state: FSMContext):
    """
    Финальный обработчик генерации персонажа.

    """
    await call.answer()
    call_data = call.data


    state_data = await state.get_data()
    char_id = state_data.get("character_id")
    bonus_dict = state_data.get("bonus_dict")

    if call_data == "tut:restart":
        await state.clear()
        await state.set_state(StartTutorial.start)
        await state.update_data(char_id=char_id)
        text = TutorialMessages.TUTORIAL_START_BUTTON
        await call.message.edit_text(
            TutorialMessages.TUTORIAL_PROMPT_TEXT,
            parse_mode='HTML',
            reply_markup=tutorial_kb(text)
        )

    elif call_data == "tut:continue":

        if not char_id or not bonus_dict:
            await state.clear()
            return await call.message.edit_text(
                f"⚠️ Ошибка: Данные создания утеряны. Начните заново цепочку создания персонажа")

        async with get_db_connection() as db:
            char_stats_repo = get_character_stats_repo(db)
            final_stats_obj = await char_stats_repo.add_stats(char_id, bonus_dict)

        if final_stats_obj:
            # Превращаем DTO в словарь для .format()
            final_stats_for_text = {
                "strength"      : final_stats_obj.strength,
                "perception"    : final_stats_obj.perception,
                "endurance"     : final_stats_obj.endurance,
                "charisma"      : final_stats_obj.charisma,
                "intelligence"  : final_stats_obj.intelligence,
                "agility"       : final_stats_obj.agility,
                "luck"          : final_stats_obj.luck,
            }
        else:
            await state.clear()
            return await call.message.edit_text(
                f"⚠️ Ошибка: Данные создания утеряны. Начните заново цепочку создания персонажа")

        text = TutorialMessages.TUTORIAL_COMPLETE_TEXT.format(**final_stats_for_text)

        if isinstance(call.message, Message):
            await call.message.edit_text(
                text=text,
                parse_mode='HTML',
                reply_markup=tutorial_kb(TutorialMessages.TUTORIAL_CONFIRM_BUTTONS)
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


    return None



