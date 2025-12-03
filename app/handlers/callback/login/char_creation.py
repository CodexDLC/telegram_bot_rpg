import time
from typing import Any, cast

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from app.resources.fsm_states.states import CharacterCreation, StartTutorial
from app.resources.keyboards.inline_kb.loggin_und_new_character import confirm_kb
from app.resources.schemas_dto.character_dto import CharacterOnboardingUpdateDTO
from app.resources.schemas_dto.fsm_state_dto import SessionDataDTO
from app.resources.texts.game_messages.lobby_messages import LobbyMessages
from app.resources.texts.game_messages.tutorial_messages import TutorialMessages
from app.services.core_service.manager.account_manager import AccountManager
from app.services.helpers_module.callback_exceptions import UIErrorHandler as Err
from app.services.helpers_module.dto_helper import FSM_CONTEXT_KEY
from app.services.helpers_module.game_validator import validate_character_name
from app.services.ui_service.helpers_ui.ui_animation_service import UIAnimationService
from app.services.ui_service.helpers_ui.ui_tools import await_min_delay
from app.services.ui_service.menu_service import MenuService
from app.services.ui_service.navigation_service import DEFAULT_SPAWN_POINT
from app.services.ui_service.new_character.onboarding_service import OnboardingService

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
    """
    Инициирует FSM создания нового персонажа.
    """
    log.info(f"CharCreation | status=started user_id={user_id} char_id={char_id}")
    await call.answer()
    start_time = time.monotonic()

    # --- FIX START: Сохраняем контекст, а не перезаписываем его ---
    current_state_data = await state.get_data()
    session_context = current_state_data.get(FSM_CONTEXT_KEY, {})

    session_context.update(
        {"user_id": user_id, "char_id": char_id, "message_menu": message_menu}
    )  # Явно сохраняем переданное меню

    await state.update_data({FSM_CONTEXT_KEY: session_context})
    # --- FIX END ---

    ms = MenuService(
        game_stage="creation",
        state_data=await state.get_data(),
        session=session,
        account_manager=account_manager,
    )
    text, kb = await ms.get_data_menu()
    log.debug(f"CharCreation | component=menu_data status=generated user_id={user_id}")

    await await_min_delay(start_time, min_delay=0.3)

    if not message_menu.get("chat_id") or not message_menu.get("message_id"):
        log.error(f"CharCreation | status=failed reason='Invalid message_menu' user_id={user_id} data='{message_menu}'")
        await Err.generic_error(call=call)
        return

    await bot.edit_message_text(
        chat_id=message_menu["chat_id"],
        message_id=message_menu["message_id"],
        text=text,
        parse_mode="html",
        reply_markup=kb,
    )
    log.debug(f"UIRender | component=menu_message status=updated user_id={user_id}")

    await create_message_content_start_creation(user_id=user_id, call=call, state=state, bot=bot)

    await state.set_state(CharacterCreation.choosing_gender)
    log.info(f"FSM | state=CharacterCreation.choosing_gender user_id={user_id}")


async def create_message_content_start_creation(call: CallbackQuery, state: FSMContext, user_id: int, bot: Bot) -> None:
    """
    Создает или редактирует контентное сообщение для этапа создания персонажа.
    """
    log.debug(f"CharCreation | action=render_content_message user_id={user_id}")
    start_time = time.monotonic()

    create_service = OnboardingService(user_id=user_id)
    text, kb = create_service.get_data_start_creation_content()

    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    message_content: dict[str, Any] | None = session_context.get("message_content")

    await await_min_delay(start_time, min_delay=0.3)

    if message_content is None:
        log.debug(f"CharCreation | reason='message_content not found' action=create_new user_id={user_id}")
        if call.message:
            msg = await call.message.answer(text=text, parse_mode="html", reply_markup=kb)
            message_content = {"chat_id": msg.chat.id, "message_id": msg.message_id}
            session_context["message_content"] = message_content
            await state.update_data({FSM_CONTEXT_KEY: session_context})
            log.info(f"UIRender | component=content_message status=created msg_id={msg.message_id} user_id={user_id}")
    else:
        log.debug(f"CharCreation | action=edit_existing user_id={user_id} msg_id={message_content.get('message_id')}")
        try:
            await bot.edit_message_text(
                chat_id=message_content["chat_id"],
                message_id=message_content["message_id"],
                text=text,
                parse_mode="html",
                reply_markup=kb,
            )
        except TelegramAPIError:
            log.exception(f"CharCreation | status=failed reason='edit_message_text failed' user_id={user_id}")
            await Err.char_id_not_found_in_fsm(call=call)


@router.callback_query(CharacterCreation.choosing_gender, F.data.startswith("gender:"))
async def choose_gender_handler(call: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    """
    Обрабатывает выбор пола персонажа и запрашивает имя.
    """
    if not call.from_user or not call.data:
        return

    user_id = call.from_user.id
    log.info(f"CharCreation | event=gender_selected user_id={user_id} data='{call.data}'")
    await call.answer()
    start_time = time.monotonic()

    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    char_id = session_context.get("char_id")
    message_content: dict[str, Any] | None = session_context.get("message_content")

    if not isinstance(char_id, int) or not isinstance(message_content, dict):
        log.warning(f"CharCreation | status=failed reason='Invalid FSM data' user_id={user_id} data='{state_data}'")
        await Err.generic_error(call=call)
        return

    create_service = OnboardingService(user_id=user_id, char_id=char_id)
    text, gender_display, gender_db = create_service.get_data_start_gender(gender_callback=call.data)
    log.debug(f"CharCreation | gender_selected='{gender_db}' user_id={user_id}")

    await await_min_delay(start_time, min_delay=0.3)

    await bot.edit_message_text(
        chat_id=message_content["chat_id"],
        message_id=message_content["message_id"],
        text=text,
        parse_mode="html",
        reply_markup=None,
    )
    await state.update_data(gender_db=gender_db, gender_display=gender_display)
    await state.set_state(CharacterCreation.choosing_name)
    log.info(f"FSM | state=CharacterCreation.choosing_name user_id={user_id}")


@router.message(CharacterCreation.choosing_name)
async def choosing_name_handler(m: Message, state: FSMContext, bot: Bot) -> None:
    """
    Обрабатывает ввод имени персонажа, валидирует его и запрашивает подтверждение.
    """
    if not m.from_user or not m.text:
        return

    user_id = m.from_user.id
    name = m.text.strip()
    log.info(f"CharCreation | event=name_input user_id={user_id} name='{name}'")

    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    message_content: dict[str, Any] | None = session_context.get("message_content")

    if not isinstance(message_content, dict):
        log.warning(f"CharCreation | status=failed reason='Invalid FSM data' user_id={user_id} data='{state_data}'")
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
        log.info(f"FSM | state=CharacterCreation.confirm user_id={user_id}")

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
    """
    Финальное подтверждение создания персонажа.
    Сохраняет данные в БД и запускает туториал.
    """
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
        log.error(f"CharCreation | status=failed reason='Incomplete FSM data' user_id={user_id} data='{state_data}'")
        await state.clear()
        await Err.generic_error(call=call)
        return

    await state.set_state(StartTutorial.start)
    log.info(f"FSM | state=StartTutorial.start user_id={user_id}")

    char_update_dto = CharacterOnboardingUpdateDTO(
        name=cast(str, name), gender=cast(Any, gender_db), game_stage="tutorial_stats"
    )
    create_service = OnboardingService(user_id=user_id, char_id=char_id)

    await create_service.update_character_db(session=session, char_update_dto=char_update_dto)
    log.info(f"DBUpdate | entity=character status=success char_id={char_id}")

    await account_manager.update_account_fields(char_id, {"location_id": DEFAULT_SPAWN_POINT})
    log.info(f"RedisUpdate | entity=account status=success char_id={char_id} location_id='{DEFAULT_SPAWN_POINT}'")

    message_menu = session_context.get("message_menu")
    message_content = session_context.get("message_content")

    clean_session_data = {
        "user_id": user_id,
        "char_id": char_id,
        "message_menu": message_menu,
        "message_content": message_content,
    }
    await state.set_data({FSM_CONTEXT_KEY: clean_session_data})
    log.debug(f"FSM | action=cleanup reason=creation_finished user_id={user_id}")

    if not isinstance(message_content, dict):
        log.error(f"CharCreation | status=failed reason='message_content is not a dict' user_id={user_id}")
        await Err.generic_error(call)
        return

    session_dto = SessionDataDTO(**session_context)
    anim_service = UIAnimationService(bot=bot, message_data=session_dto)
    await anim_service.animate_sequence(sequence=TutorialMessages.WAKING_UP_SEQUENCE, final_kb=None)
    log.debug(f"Tutorial | animation=waking_up status=finished user_id={user_id}")

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
