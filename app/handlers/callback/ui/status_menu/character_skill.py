# app/handlers/callback/ui/status_menu/character_skill.py
import logging

from aiogram import Router, F, Bot
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.resources.fsm_states.states import FSM_CONTEX_CHARACTER_STATUS
from app.resources.keyboards.callback_data import StatusMenuCallback
from app.resources.texts.ui_text.data_text_status_menu import STATUS_SKILLS
from app.services.helpers_module.get_data_handlers.status_data_helper import get_status_data_package
from app.services.helpers_module.helper_id_callback import error_int_id, get_int_id_type, get_group_key, \
    get_type_callback
from app.services.ui_service.character_skill_service import CharacterSkillStatusService

log = logging.getLogger(__name__)

router = Router(name="character_skill_menu")


@router.callback_query(
    StatusMenuCallback.filter(F.action == "skills"), # <--- ФИЛЬТР ДЛЯ ФИЛЬТРА
    StateFilter(*FSM_CONTEX_CHARACTER_STATUS)
)
async def character_skill_status_handler(
    call: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    callback_data: StatusMenuCallback
):
    """
    Обработка callback кнопок в меню статус, относящихся c навыкам персонажа.

    """
    log.info("character_skill_status_handler начал свою работу")

    char_id = callback_data.char_id
    call_type = callback_data.action
    view_mode = callback_data.view_mode

    if char_id is None:
        # вызываем функцию helper ошибки айди
        log.error(f"Ошибка: ID персонажа не найден в callback_data: {call.data}")
        await error_int_id(call)
        return

    state_data = await state.get_data()
    bd_data_status = state_data.get("bd_data_status") or None
    user_id = state_data.get("user_id")

    if bd_data_status is None:
        bd_data_status = await get_status_data_package(char_id=char_id, user_id=user_id)

    char_skill_service = CharacterSkillStatusService(
        char_id=char_id,
        call_type=call_type,
        view_mode=view_mode,
        character=bd_data_status.get("character"),
        character_skill=bd_data_status.get("character_progress_skill"),

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
        call_type=call_type,
        bd_data_status=bd_data_status
    )

    log.info("character_skill_status_handler Закончил свою работу")



@router.callback_query(F.data.startswith("skills:group"),
                       StateFilter(*FSM_CONTEX_CHARACTER_STATUS))
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
    user_id = call.from_user.id
    bd_data_status = state_data.get("bd_data_status") or None

    if bd_data_status is None:
        bd_data_status = await get_status_data_package(char_id=char_id, user_id=user_id)

    char_skill_service = CharacterSkillStatusService(
        char_id=char_id,
        character=bd_data_status.get("character"),
        character_skill=bd_data_status.get("character_progress_skill"),
        call_type=state_data.get("call_type"),
        view_mode=state_data.get("view_mode")
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


@router.callback_query(F.data.startswith("skill:details:"),
                       StateFilter(*FSM_CONTEX_CHARACTER_STATUS))
async def character_skill_handler(call: CallbackQuery, state: FSMContext, bot: Bot):
    pass














