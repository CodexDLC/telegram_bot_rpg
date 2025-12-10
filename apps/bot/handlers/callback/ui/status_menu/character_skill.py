import asyncio
import time

from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from apps.bot.resources.fsm_states.states import FSM_CONTEX_CHARACTER_STATUS
from apps.bot.resources.keyboards.status_callback import SkillModeCallback, StatusSkillsCallback
from apps.bot.ui_service.helpers_ui.callback_exceptions import UIErrorHandler as Err
from apps.bot.ui_service.helpers_ui.dto_helper import FSM_CONTEXT_KEY
from apps.bot.ui_service.helpers_ui.ui_animation_service import UIAnimationService
from apps.bot.ui_service.helpers_ui.ui_tools import await_min_delay
from apps.bot.ui_service.status_menu.status_skill_service import CharacterSkillStatusService
from apps.common.schemas_dto import SessionDataDTO

router = Router(name="character_skill_menu")


@router.callback_query(StatusSkillsCallback.filter(F.level == "group"), StateFilter(*FSM_CONTEX_CHARACTER_STATUS))
async def character_skill_group_handler(
    call: CallbackQuery, state: FSMContext, bot: Bot, callback_data: StatusSkillsCallback, session: AsyncSession
) -> None:
    """Обрабатывает нажатие на группу навыков и отображает список навыков в ней."""
    if not call.from_user or not call.message:
        return

    await call.answer()
    user_id = call.from_user.id
    char_id = callback_data.char_id
    key = callback_data.key
    log.info(f"SkillMenu | event=group_selected user_id={user_id} char_id={char_id} group='{key}'")

    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    session_dto = SessionDataDTO(**session_context)
    anim_service = UIAnimationService(bot=bot, message_data=session_dto)

    async def run_logic():
        try:
            char_skill_ser = CharacterSkillStatusService(char_id=char_id, key=key, state_data=state_data)
            skills_data = await char_skill_ser.get_list_skills_dto(session)

            if skills_data is None:
                log.warning(f"SkillMenu | status=failed reason='No skill data found' char_id={char_id}")
                await Err.generic_error(call=call)
                return None, None, None

            result = char_skill_ser.status_group_skill_message(character_skills=skills_data)
            if not result or not result[0] or not result[1]:
                log.error(
                    f"SkillMenu | status=failed reason='status_group_skill_message returned empty' char_id={char_id}"
                )
                await Err.generic_error(call=call)
                return None, None, None

            message_data = char_skill_ser.get_message_content_data()
            if not message_data:
                log.error(f"SkillMenu | status=failed reason='message_content not found' char_id={char_id}")
                await Err.generic_error(call=call)
                return None, None, None

            return result[0], result[1], message_data
        except (ValueError, AttributeError, TypeError, KeyError) as e:
            log.error(
                f"SkillMenu | status=failed reason='Logic error in group handler' user_id={user_id} error='{e}'",
                exc_info=True,
            )
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
    log.debug(f"UIRender | component=skill_group status=success user_id={user_id} group='{key}'")


@router.callback_query(StatusSkillsCallback.filter(F.level == "detail"), StateFilter(*FSM_CONTEX_CHARACTER_STATUS))
async def character_skill_detail_handler(
    call: CallbackQuery, state: FSMContext, bot: Bot, callback_data: StatusSkillsCallback, session: AsyncSession
) -> None:
    """Обрабатывает нажатие на конкретный навык и отображает его детальную информацию."""
    if not call.from_user:
        return

    start_time = time.monotonic()
    user_id = call.from_user.id
    char_id = callback_data.char_id
    key = callback_data.key
    log.info(f"SkillMenu | event=detail_selected user_id={user_id} char_id={char_id} skill='{key}'")

    state_data = await state.get_data()
    if not state_data:
        log.warning(f"SkillMenu | status=failed reason='State data missing' user_id={user_id}")
        await Err.callback_data_missing(call=call)
        return

    group_key = state_data.get("group_key")
    if not group_key:
        log.warning(f"SkillMenu | status=failed reason='group_key missing in state' user_id={user_id}")
        await Err.callback_data_missing(call=call)
        return

    try:
        char_skill_ser = CharacterSkillStatusService(char_id=char_id, key=key, state_data=state_data)
        skills_data = await char_skill_ser.get_list_skills_dto(session)

        if skills_data is None:
            log.warning(f"SkillMenu | status=failed reason='No skill data found for detail view' char_id={char_id}")
            await Err.generic_error(call=call)
            return

        result = char_skill_ser.status_detail_skill_message(group_key=group_key, skills_dto=skills_data)
        if not result or not result[0] or not result[1]:
            log.error(
                f"SkillMenu | status=failed reason='status_detail_skill_message returned empty' char_id={char_id}"
            )
            await Err.generic_error(call=call)
            return
        text, kb = result

        message_data = char_skill_ser.get_message_content_data()
        if not message_data:
            log.error(f"SkillMenu | status=failed reason='message_content not found for detail view' char_id={char_id}")
            await Err.generic_error(call=call)
            return
        chat_id, message_id = message_data

        await await_min_delay(start_time, min_delay=0.5)

        if text and bot is not None:
            await bot.edit_message_text(
                chat_id=chat_id, message_id=message_id, text=text, parse_mode="html", reply_markup=kb
            )
        log.debug(f"UIRender | component=skill_detail status=success user_id={user_id} skill='{key}'")

    except (ValueError, AttributeError, TypeError, KeyError) as e:
        log.error(
            f"SkillMenu | status=failed reason='Logic error in detail handler' user_id={user_id} error='{e}'",
            exc_info=True,
        )
        await Err.generic_error(call=call)


@router.callback_query(SkillModeCallback.filter(), StateFilter(*FSM_CONTEX_CHARACTER_STATUS))
async def character_skill_mode_handler(
    call: CallbackQuery, state: FSMContext, bot: Bot, callback_data: SkillModeCallback, session: AsyncSession
) -> None:
    """Обрабатывает изменение режима прокачки навыка."""
    if not call.from_user or not call.message:
        return

    user_id = call.from_user.id
    log.info(
        f"SkillMenu | event=mode_change user_id={user_id} skill='{callback_data.skill_key}' new_mode='{callback_data.new_mode}'"
    )

    await call.answer(f"Режим изменен на: {callback_data.new_mode}")

    try:
        state_data = await state.get_data()
        group_key = state_data.get("group_key")
        if not group_key:
            raise ValueError("group_key not found in FSM.")

        char_skill_ser = CharacterSkillStatusService(
            char_id=callback_data.char_id,
            key=callback_data.skill_key,
            state_data=state_data,
        )

        await char_skill_ser.set_mode_skill(session=session, mode=callback_data.new_mode)

        skills_data = await char_skill_ser.get_list_skills_dto(session)
        if not skills_data:
            raise ValueError("Failed to get skill DTOs after update.")

        result = char_skill_ser.status_detail_skill_message(
            group_key=group_key,
            skills_dto=skills_data,
        )
        if not result or not result[0] or not result[1]:
            raise ValueError("Failed to generate skill detail message.")
        text, kb = result

        if text and bot is not None:
            await bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                parse_mode="html",
                reply_markup=kb,
            )
        log.debug(f"UIRender | component=skill_detail_mode_change status=success user_id={user_id}")

    except (ValueError, AttributeError, TypeError, KeyError) as e:
        log.error(
            f"SkillMenu | status=failed reason='Error in skill mode handler' user_id={user_id} error='{e}'",
            exc_info=True,
        )
        await call.answer("Произошла ошибка при смене режима.", show_alert=True)
