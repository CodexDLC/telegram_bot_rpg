# apps/bot/handlers/callback/login/char_creation.py
import time
from typing import Any, cast

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from apps.bot.resources.fsm_states.states import CharacterCreation, StartTutorial
from apps.bot.resources.keyboards.callback_data import GenderCallback  # Новый импорт
from apps.bot.resources.keyboards.inline_kb.loggin_und_new_character import confirm_kb
from apps.bot.resources.texts.game_messages.lobby_messages import LobbyMessages
from apps.bot.resources.texts.game_messages.tutorial_messages import TutorialMessages
from apps.bot.ui_service.helpers_ui.callback_exceptions import UIErrorHandler as Err
from apps.bot.ui_service.helpers_ui.dto_helper import FSM_CONTEXT_KEY
from apps.bot.ui_service.helpers_ui.game_validator import validate_character_name
from apps.bot.ui_service.helpers_ui.ui_animation_service import UIAnimationService
from apps.bot.ui_service.helpers_ui.ui_tools import await_min_delay
from apps.bot.ui_service.menu_service import MenuService
from apps.bot.ui_service.new_character.onboarding_service import OnboardingService
from apps.common.schemas_dto import CharacterOnboardingUpdateDTO, SessionDataDTO
from apps.common.services.core_service.manager.account_manager import AccountManager

router = Router(name="character_creation_fsm")


async def start_creation_handler(
    call: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    user_id: int,
    char_id: int,
    message_menu: dict[str, Any],
    session: AsyncSession,
    account_manager: AccountManager,
) -> None:
    log.info(f"CharCreation | status=started user_id={user_id} char_id={char_id}")
    await call.answer()
    start_time = time.monotonic()
    current_state_data = await state.get_data()
    session_context = current_state_data.get(FSM_CONTEXT_KEY, {})
    session_context.update({"user_id": user_id, "char_id": char_id, "message_menu": message_menu})
    await state.update_data({FSM_CONTEXT_KEY: session_context})
    ms = MenuService(
        game_stage="creation",
        state_data=await state.get_data(),
        session=session,
        account_manager=account_manager,
    )
    text, kb = await ms.get_data_menu()
    await await_min_delay(start_time, min_delay=0.3)
    if not message_menu.get("chat_id") or not message_menu.get("message_id"):
        await Err.generic_error(call=call)
        return
    await bot.edit_message_text(
        chat_id=message_menu["chat_id"],
        message_id=message_menu["message_id"],
        text=text,
        parse_mode="html",
        reply_markup=kb,
    )
    await create_message_content_start_creation(user_id=user_id, call=call, state=state, bot=bot)
    await state.set_state(CharacterCreation.choosing_gender)
    log.info(f"FSM | state=CharacterCreation.choosing_gender user_id={user_id}")


async def create_message_content_start_creation(call: CallbackQuery, state: FSMContext, user_id: int, bot: Bot) -> None:
    log.debug(f"CharCreation | action=render_content_message user_id={user_id}")
    start_time = time.monotonic()
    create_service = OnboardingService(user_id=user_id)
    text, kb = create_service.get_data_start_creation_content()
    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    message_content: dict[str, Any] | None = session_context.get("message_content")
    await await_min_delay(start_time, min_delay=0.3)
    if message_content is None:
        if call.message:
            msg = await call.message.answer(text=text, parse_mode="html", reply_markup=kb)
            message_content = {"chat_id": msg.chat.id, "message_id": msg.message_id}
            session_context["message_content"] = message_content
            await state.update_data({FSM_CONTEXT_KEY: session_context})
    else:
        try:
            await bot.edit_message_text(
                chat_id=message_content["chat_id"],
                message_id=message_content["message_id"],
                text=text,
                parse_mode="html",
                reply_markup=kb,
            )
        except TelegramAPIError:
            await Err.char_id_not_found_in_fsm(call=call)


@router.callback_query(CharacterCreation.choosing_gender, GenderCallback.filter())  # ИЗМЕНЕНО
async def choose_gender_handler(
    call: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    callback_data: GenderCallback,  # ИЗМЕНЕНО
) -> None:
    if not call.from_user or not call.data:
        return
    user_id = call.from_user.id
    gender_value = callback_data.value  # ИЗМЕНЕНО
    log.info(f"CharCreation | event=gender_selected user_id={user_id} data='{gender_value}'")
    await call.answer()
    start_time = time.monotonic()
    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    char_id = session_context.get("char_id")
    message_content: dict[str, Any] | None = session_context.get("message_content")
    if not isinstance(char_id, int) or not isinstance(message_content, dict):
        await Err.generic_error(call=call)
        return

    # Теперь передаем чистое значение 'male' или 'female'
    create_service = OnboardingService(user_id=user_id, char_id=char_id)
    text, gender_display = create_service.get_data_start_gender(gender_value=gender_value)

    await await_min_delay(start_time, min_delay=0.3)
    await bot.edit_message_text(
        chat_id=message_content["chat_id"],
        message_id=message_content["message_id"],
        text=text,
        parse_mode="html",
        reply_markup=None,
    )
    await state.update_data(gender_db=gender_value, gender_display=gender_display)  # ИЗМЕНЕНО
    await state.set_state(CharacterCreation.choosing_name)
    log.info(f"FSM | state=CharacterCreation.choosing_name user_id={user_id}")


@router.message(CharacterCreation.choosing_name)
async def choosing_name_handler(m: Message, state: FSMContext, bot: Bot) -> None:
    if not m.from_user or not m.text:
        return
    user_id = m.from_user.id
    name = m.text.strip()
    log.info(f"CharCreation | event=name_input user_id={user_id} name='{name}'")
    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    message_content: dict[str, Any] | None = session_context.get("message_content")
    if not isinstance(message_content, dict):
        return
    chat_id = message_content.get("chat_id")
    if not chat_id:
        return
    try:
        await bot.delete_message(chat_id=chat_id, message_id=m.message_id)
    except TelegramAPIError as e:
        log.warning(f"CharCreation | action=delete_message status=failed user_id={user_id} error='{e}'")
    is_valid, error_msg = validate_character_name(name)
    if is_valid:
        log.info(f"CharCreation | validation=success user_id={user_id} name='{name}'")
        await state.update_data(name=name)
        await state.set_state(CharacterCreation.confirm)
        text = LobbyMessages.NewCharacter.FINAL_CONFIRMATION.format(
            name=name, gender=state_data.get("gender_display", "")
        )
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_content.get("message_id"),
            text=text,
            parse_mode="HTML",
            reply_markup=confirm_kb(),
        )
    else:
        log.warning(f"CharCreation | validation=failed user_id={user_id} name='{name}' reason='{error_msg}'")
        text = f"<b>⚠️ Ошибка:</b> {error_msg}\n\n{LobbyMessages.NewCharacter.NAME_INPUT}"
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_content.get("message_id"),
            text=text,
            parse_mode="HTML",
            reply_markup=None,
        )


@router.callback_query(CharacterCreation.confirm, F.data == "confirm")
async def confirm_creation_handler(
    call: CallbackQuery, state: FSMContext, bot: Bot, session: AsyncSession, account_manager: AccountManager
) -> None:
    if not call.from_user:
        return
    user_id = call.from_user.id
    log.info(f"CharCreation | event=confirmed user_id={user_id}")
    await call.answer()
    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    char_id = session_context.get("char_id")
    name = state_data.get("name")
    gender_db = state_data.get("gender_db")
    gender_display = state_data.get("gender_display")
    if not all([isinstance(char_id, int), isinstance(name, str), isinstance(gender_db, str)]):
        await state.clear()
        await Err.generic_error(call=call)
        return
    await state.set_state(StartTutorial.start)
    log.info(f"FSM | state=StartTutorial.start user_id={user_id}")
    char_update_dto = CharacterOnboardingUpdateDTO(
        name=cast(str, name), gender=cast(Any, gender_db), game_stage="tutorial_stats"
    )
    create_service = OnboardingService(user_id=user_id, char_id=char_id, account_manager=account_manager)
    await create_service.finalize_character_creation(session=session, char_update_dto=char_update_dto)
    message_menu = session_context.get("message_menu")
    message_content = session_context.get("message_content")
    clean_session_data = {
        "user_id": user_id,
        "char_id": char_id,
        "message_menu": message_menu,
        "message_content": message_content,
    }
    await state.set_data({FSM_CONTEXT_KEY: clean_session_data})
    if not isinstance(message_content, dict):
        await Err.generic_error(call)
        return
    session_dto = SessionDataDTO(**session_context)
    anim_service = UIAnimationService(bot=bot, message_data=session_dto)
    await anim_service.animate_sequence(sequence=TutorialMessages.WAKING_UP_SEQUENCE, final_kb=None)
    if name and gender_display is not None:
        text, kb = create_service.get_data_start(name=name, gender=gender_display)
    else:
        text, kb = "ошибка", None
        await Err.generic_error(call=call)
    await bot.edit_message_text(
        chat_id=message_content.get("chat_id"),
        message_id=message_content.get("message_id"),
        text=text,
        parse_mode="HTML",
        reply_markup=kb,
    )
    log.debug(f"Tutorial | component=start_message status=rendered user_id={user_id}")
