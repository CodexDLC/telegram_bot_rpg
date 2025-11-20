# app/handlers/callback/ui/status_menu/character_skill.py
import asyncio

from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from app.resources.fsm_states.states import FSM_CONTEX_CHARACTER_STATUS
from app.resources.keyboards.status_callback import SkillModeCallback, StatusSkillsCallback
from app.resources.schemas_dto.fsm_state_dto import SessionDataDTO
from app.services.helpers_module.callback_exceptions import UIErrorHandler as Err
from app.services.helpers_module.dto_helper import FSM_CONTEXT_KEY
from app.services.ui_service.helpers_ui.ui_animation_service import UIAnimationService
from app.services.ui_service.helpers_ui.ui_tools import await_min_delay
from app.services.ui_service.status_menu.status_skill_service import CharacterSkillStatusService

router = Router(name="character_skill_menu")


@router.callback_query(StatusSkillsCallback.filter(F.level == "group"), StateFilter(*FSM_CONTEX_CHARACTER_STATUS))
async def character_skill_group_handler(
    call: CallbackQuery, state: FSMContext, bot: Bot, callback_data: StatusSkillsCallback, session: AsyncSession
) -> None:
    """
    Обрабатывает нажатие на группу навыков и отображает список навыков в ней.
    """
    if not call.from_user or not call.message:
        log.warning("Handler 'character_skill_group_handler' received an update without 'from_user' or 'message'.")
        return

    await call.answer()
    user_id = call.from_user.id
    char_id = callback_data.char_id
    key = callback_data.key
    log.info(f"User {user_id} triggered 'character_skill_group_handler' for char_id={char_id}, key='{key}'.")

    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    session_dto = SessionDataDTO(**session_context)
    anim_service = UIAnimationService(bot=bot, message_data=session_dto)

    async def run_logic():
        try:
            char_skill_ser = CharacterSkillStatusService(char_id=char_id, key=key, state_data=state_data)
            skills_data = await char_skill_ser.get_list_skills_dto(session)

            if skills_data is None:
                log.warning(f"No skill data found for char_id={char_id}.")
                await Err.generic_error(call=call)
                return None, None, None

            result = char_skill_ser.status_group_skill_message(character_skills=skills_data)
            if not result or not result[0] or not result[1]:
                await Err.generic_error(call=call)
                return None, None, None

            message_data = char_skill_ser.get_message_content_data()
            if not message_data:
                await Err.generic_error(call=call)
                return None, None, None

            return result[0], result[1], message_data
        except (ValueError, AttributeError, TypeError, KeyError) as e:
            log.error(f"An error occurred in 'character_skill_group_handler' for user {user_id}: {e}", exc_info=True)
            await Err.generic_error(call=call)
            return None, None, None

    results = await asyncio.gather(
        anim_service.animate_loading(duration=1.0, text="📚 <b>Загрузка...</b>"),
        run_logic(),
    )

    text, kb, message_data = results[1]
    if text is None:
        return

    chat_id, message_id = message_data
    await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=kb)
    await state.update_data(group_key=key)
    log.debug(f"Successfully displayed skill group '{key}' for char_id={char_id}.")


@router.callback_query(StatusSkillsCallback.filter(F.level == "detail"), StateFilter(*FSM_CONTEX_CHARACTER_STATUS))
async def character_skill_detail_handler(
    call: CallbackQuery, state: FSMContext, bot: Bot, callback_data: StatusSkillsCallback, session: AsyncSession
) -> None:
    """
    Обрабатывает нажатие на конкретный навык и отображает его детальную информацию.
    """
    if not call.from_user:
        log.warning("Handler 'character_skill_detail_handler' received an update without 'from_user'.")
        return

    start_time = asyncio.get_event_loop().time()
    user_id = call.from_user.id
    char_id = callback_data.char_id
    key = callback_data.key
    log.info(f"User {user_id} triggered 'character_skill_detail_handler' for char_id={char_id}, key='{key}'.")

    state_data = await state.get_data()
    if not state_data:
        log.warning(f"State data is missing for user {user_id} in 'character_skill_detail_handler'.")
        await Err.callback_data_missing(call=call)
        return

    group_key = state_data.get("group_key")
    if not group_key:
        log.warning(f"'group_key' is missing in state data for user {user_id}.")
        await Err.callback_data_missing(call=call)
        return

    try:
        char_skill_ser = CharacterSkillStatusService(char_id=char_id, key=key, state_data=state_data)
        skills_data = await char_skill_ser.get_list_skills_dto(session)

        if skills_data is None:
            log.warning(f"No skill data found for char_id={char_id}. Aborting detail view.")
            await Err.generic_error(call=call)
            return

        result = char_skill_ser.status_detail_skill_message(group_key=group_key, skills_dto=skills_data)
        if not result or not result[0] or not result[1]:
            await Err.generic_error(call=call)
            return
        text, kb = result

        message_data = char_skill_ser.get_message_content_data()
        if not message_data:
            await Err.generic_error(call=call)
            return
        chat_id, message_id = message_data

        await await_min_delay(start_time, min_delay=0.5)

        if text and bot is not None:
            await bot.edit_message_text(
                chat_id=chat_id, message_id=message_id, text=text, parse_mode="html", reply_markup=kb
            )
        log.debug(f"Successfully displayed skill detail '{key}' for char_id={char_id}.")

    except (ValueError, AttributeError, TypeError, KeyError) as e:
        log.error(f"An error occurred in 'character_skill_detail_handler' for user {user_id}: {e}", exc_info=True)
        await Err.generic_error(call=call)


@router.callback_query(SkillModeCallback.filter(), StateFilter(*FSM_CONTEX_CHARACTER_STATUS))
async def character_skill_mode_handler(
    call: CallbackQuery, state: FSMContext, bot: Bot, callback_data: SkillModeCallback, session: AsyncSession
) -> None:
    """
    Обрабатывает изменение режима прокачки и ПОЛНОСТЬЮ ОБНОВЛЯЕТ
    сообщение, чтобы показать новое состояние.
    """
    if not call.from_user or not call.message:
        log.warning("Handler 'character_skill_mode_handler' received update without 'from_user' or 'message'.")
        return

    user_id = call.from_user.id
    log.info(f"User {user_id} changing skill '{callback_data.skill_key}' to '{callback_data.new_mode}'.")

    await call.answer(f"Режим изменен на: {callback_data.new_mode}")

    try:
        state_data = await state.get_data()
        group_key = state_data.get("group_key")
        if not group_key:
            raise ValueError("group_key не найден в FSM, не могу построить 'Назад'")

        char_skill_ser = CharacterSkillStatusService(
            char_id=callback_data.char_id,
            key=callback_data.skill_key,
            state_data=state_data,
        )

        await char_skill_ser.set_mode_skill(session=session, mode=callback_data.new_mode)

        skills_data = await char_skill_ser.get_list_skills_dto(session)
        if not skills_data:
            raise ValueError("Не удалось получить DTO навыков после обновления")

        result = char_skill_ser.status_detail_skill_message(
            group_key=group_key,
            skills_dto=skills_data,
        )
        if not result or not result[0] or not result[1]:
            raise ValueError("Не удалось сгенерировать сообщение с деталями навыка")
        text, kb = result

        if text and bot is not None:
            await bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                parse_mode="html",
                reply_markup=kb,
            )
        log.debug("Сообщение с деталями навыка успешно обновлено.")

    except (ValueError, AttributeError, TypeError, KeyError) as e:
        log.error(f"Ошибка в skill_mode_handler: {e}", exc_info=True)
        await call.answer("Произошла ошибка при смене режима.", show_alert=True)
