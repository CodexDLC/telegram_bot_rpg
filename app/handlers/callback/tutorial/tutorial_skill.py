import asyncio
from typing import Any

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger as log
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.resources.fsm_states.states import CharacterLobby, StartTutorial
from app.resources.keyboards.callback_data import TutorialQuestCallback
from app.resources.schemas_dto.fsm_state_dto import SessionDataDTO
from app.services.helpers_module.callback_exceptions import UIErrorHandler as Err
from app.services.helpers_module.dto_helper import FSM_CONTEXT_KEY, fsm_clean_core_state
from app.services.ui_service.helpers_ui.ui_animation_service import UIAnimationService
from app.services.ui_service.tutorial.tutorial_service_skill import TutorialServiceSkills

router = Router(name="tutorial_skill_router")


@router.callback_query(StartTutorial.confirmation, F.data == "tut_quest:start_skill_phase")
async def start_skill_phase_handler(call: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    """Начинает фазу выбора навыков в туториале."""
    if not call.from_user:
        return

    user_id = call.from_user.id
    log.info(f"TutorialSkill | event=start_phase user_id={user_id}")
    await call.answer()

    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    message_content: dict[str, Any] | None = session_context.get("message_content")

    if not message_content or "chat_id" not in message_content or "message_id" not in message_content:
        log.error(f"TutorialSkill | status=failed reason='message_content not found' user_id={user_id}")
        await Err.message_content_not_found_in_fsm(call=call)
        return

    session_dto = SessionDataDTO(**session_context)
    anim_service = UIAnimationService(bot=bot, message_data=session_dto)

    async def run_logic():
        skill_choices_list: list[str] = []
        await state.update_data(skill_choices_list=skill_choices_list)
        tut_service = TutorialServiceSkills(skills_db=skill_choices_list)
        result = tut_service.get_start_data()
        if not result or not result[0] or not result[1]:
            await Err.generic_error(call)
            return None, None
        return result

    results = await asyncio.gather(
        anim_service.animate_loading(duration=1.0, text="📜 <b>Подготовка...</b>"),
        run_logic(),
    )

    text, kb = results[1]
    if text is None:
        return

    await bot.edit_message_text(
        chat_id=message_content["chat_id"],
        message_id=message_content["message_id"],
        text=text,
        parse_mode="html",
        reply_markup=kb,
    )

    await state.set_state(StartTutorial.in_skills_progres)
    log.info(f"FSM | state=StartTutorial.in_skills_progres user_id={user_id}")


@router.callback_query(StartTutorial.in_skills_progres, TutorialQuestCallback.filter())
async def in_skills_progres_handler(
    call: CallbackQuery, state: FSMContext, callback_data: TutorialQuestCallback, bot: Bot
) -> None:
    """Обрабатывает шаги пользователя в процессе выбора навыков."""
    if not call.from_user:
        return

    user_id = call.from_user.id
    log.info(f"TutorialSkill | event=step user_id={user_id} data='{callback_data.model_dump_json()}'")
    await call.answer()

    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    message_content: dict[str, Any] | None = session_context.get("message_content")

    if not message_content or "chat_id" not in message_content or "message_id" not in message_content:
        log.error(f"TutorialSkill | status=failed reason='message_content not found' user_id={user_id}")
        await Err.message_content_not_found_in_fsm(call=call)
        return

    session_dto = SessionDataDTO(**session_context)
    anim_service = UIAnimationService(bot=bot, message_data=session_dto)

    async def run_logic():
        try:
            skill_choices_list: list[str] = state_data.get("skill_choices_list", [])
            tut_service = TutorialServiceSkills(callback_data=callback_data, skills_db=skill_choices_list)
            result = tut_service.get_next_data()
            if not result or not result[0] or not result[1]:
                raise ValueError("Failed to get next tutorial step data.")
            text, kb = result

            updated_skills = tut_service.get_skills_db()
            await state.update_data(skill_choices_list=updated_skills)
            log.debug(f"FSM | data_updated key=skill_choices_list user_id={user_id} skills='{updated_skills}'")
            return text, kb
        except ValueError as e:
            log.error(f"TutorialSkill | status=failed reason='{e}' user_id={user_id}", exc_info=True)
            await call.answer("Произошла ошибка при обработке вашего выбора. Попробуйте снова.", show_alert=True)
            return None, None

    results = await asyncio.gather(
        anim_service.animate_loading(duration=1.5, text="⏳ <b>Следующий шаг...</b>"),
        run_logic(),
    )

    text, kb = results[1]
    if text is None:
        return

    if isinstance(text, str):
        await bot.edit_message_text(
            chat_id=message_content["chat_id"],
            message_id=message_content["message_id"],
            text=text,
            parse_mode="html",
            reply_markup=kb,
        )
    elif isinstance(text, list):
        if all(isinstance(item, tuple) and len(item) == 2 for item in text):
            await anim_service.animate_sequence(sequence=tuple(text), final_kb=kb)
        else:
            log.error(f"TutorialSkill | status=failed reason='Invalid animation sequence format' user_id={user_id}")
            await Err.generic_error(call=call)
            return
    else:
        log.error(
            f"TutorialSkill | status=failed reason='Unexpected data type from service' type='{type(text)}' user_id={user_id}"
        )
        await Err.generic_error(call=call)
        return

    if callback_data.phase == "finale":
        await state.set_state(StartTutorial.skill_confirm)
        log.info(f"FSM | state=StartTutorial.skill_confirm user_id={user_id}")


@router.callback_query(StartTutorial.skill_confirm, TutorialQuestCallback.filter(F.phase == "p_end"))
async def skill_confirm_handler(
    call: CallbackQuery, state: FSMContext, callback_data: TutorialQuestCallback, bot: Bot, session: AsyncSession
) -> None:
    """Обрабатывает финальный выбор в туториале по навыкам."""
    if not call.from_user or not call.message:
        return

    await call.answer()

    final_choice = callback_data.value
    user_id = call.from_user.id
    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    char_id = session_context.get("char_id")
    skill_choices_list: list[str] = state_data.get("skill_choices_list", [])
    message_content: dict[str, Any] | None = session_context.get("message_content")

    log.info(f"TutorialSkill | event=confirm user_id={user_id} char_id={char_id} choice='{final_choice}'")

    if not char_id or not message_content:
        log.error(f"TutorialSkill | status=failed reason='char_id or message_content not found' user_id={user_id}")
        await Err.generic_error(call=call)
        return

    if final_choice:
        skill_choices_list.append(final_choice)

    log.debug(f"TutorialSkill | final_choices='{skill_choices_list}' char_id={char_id}")

    session_dto = SessionDataDTO(**session_context)
    anim_service = UIAnimationService(bot=bot, message_data=session_dto)
    tut_service = TutorialServiceSkills(skills_db=skill_choices_list)

    async def run_logic():
        try:
            await tut_service.finalize_skill_selection(session=session, char_id=char_id)
            log.info(f"DBUpdate | entity=skill_selection status=success char_id={char_id}")
            return tut_service.get_awakening_data(char_id=char_id, final_choice_key=final_choice)
        except SQLAlchemyError:
            log.exception(f"DBUpdate | entity=skill_selection status=failed char_id={char_id}")
            await Err.generic_error(call=call)
            return None, None

    results = await asyncio.gather(
        anim_service.animate_loading(duration=2.0, text="💾 <b>Сохранение выбора...</b>"),
        run_logic(),
    )

    text, kb = results[1]
    if text is None:
        return

    await bot.edit_message_text(
        chat_id=message_content["chat_id"],
        message_id=message_content["message_id"],
        text=text,
        parse_mode="html",
        reply_markup=kb,
    )
    log.debug(f"UIRender | component=awakening_message status=rendered user_id={user_id}")

    await fsm_clean_core_state(state=state, event_source=call)
    log.debug(f"FSM | action=cleanup reason=tutorial_finished user_id={user_id}")

    await state.set_state(CharacterLobby.selection)
    log.info(f"FSM | state=CharacterLobby.selection reason=tutorial_finished user_id={user_id}")
