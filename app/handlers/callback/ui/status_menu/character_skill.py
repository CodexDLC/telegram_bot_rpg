# app/handlers/callback/ui/status_menu/character_skill.py
import logging

from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.resources.fsm_states.states import FSM_CONTEX_CHARACTER_STATUS
from app.services.helpers_module.DTO_helper import fsm_convector
from app.services.helpers_module.helper_id_callback import error_int_id, get_int_id_type, get_group_key, \
    get_type_callback
from app.services.ui_service.character_skill_service import CharacterSkillStatusServer

log = logging.getLogger(__name__)

router = Router(name="character_skill_menu")


@router.callback_query(F.data.startswith("status:skills"),
                       *FSM_CONTEX_CHARACTER_STATUS)

async def character_skill_status_handler(call: CallbackQuery, state: FSMContext, bot: Bot):
    """
    Обработка callback кнопок в меню статус, относящихся c навыкам персонажа.

    """
    log.info("character_skill_status_handler начал свою работу")

    char_id = get_int_id_type(call=call)
    t_data = get_type_callback(call=call)

    if char_id is None:
        # вызываем функцию helper ошибки айди
        log.error(f"Ошибка: ID персонажа не найден в callback_data: {call.data}")
        await error_int_id(call)
        return

    state_data = await state.get_data()
    character_skill = await fsm_convector(state_data.get("character_progress_skill"), "character_progress")
    character = await fsm_convector(state_data.get("character"), "character")
    state_fsm = state_data.get("state_data")

    char_skill_service = CharacterSkillStatusServer(
        char_id=char_id,
        state_fsm=state_fsm,
        character=character,
        character_skill=character_skill,
        call_type=t_data
    )

    text, kb = char_skill_service.data_message_all_group_skill()

    message_content = state_data.get("message_content") or None

    if message_content is not None:

        await bot.edit_message_text(
            chat_id=message_content.get("chat_id"),
            message_id=message_content.get("message_id"),
            text=text,
            parse_mode='HTML',
            reply_markup=kb
        )

    await state.update_data(
        char_id=char_id,
        state_fsm=state_fsm,
        call_type=t_data
    )

    log.info("character_skill_status_handler Закончил свою работу")



@router.callback_query(F.data.startswith("status:skills:group"),
                       *FSM_CONTEX_CHARACTER_STATUS)
async def character_skill_group_handler(call: CallbackQuery, state: FSMContext, bot: Bot):
    """
    Обработчик кнопок
    """

    gp = get_group_key(call)

    if gp is None:
        # вызываем функцию helper ошибки айди
        log.error(f"Ошибка: ID персонажа не найден в callback_data: {call.data}")
        await error_int_id(call)
        return



    state_data = await state.get_data()
    char_id = state_data.get("char_id")
    state_fsm = state_data.get("state_fsm")
    character_skill = await fsm_convector(state_data.get("character_progress_skill"), "character_progress")
    character = await fsm_convector(state_data.get("character"), "character")
    t_data = get_type_callback(call=call)


    char_skill_service = CharacterSkillStatusServer(
        char_id=char_id,
        state_fsm=state_fsm,
        character=character,
        character_skill=character_skill,
        call_type=t_data,
    )

    text, kb = char_skill_service.data_message_group_skill(group_type=gp)

    message_content = state_data.get("message_content") or None

    if message_content is not None:

        await bot.edit_message_text(
            chat_id=message_content.get("chat_id"),
            message_id=message_content.get("message_id"),
            text=text,
            parse_mode='HTML',
            reply_markup=kb
        )
















