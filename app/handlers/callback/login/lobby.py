import time
from typing import Any

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger as log
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.handlers.callback.login.char_creation import start_creation_handler
from app.resources.fsm_states.states import CharacterLobby
from app.resources.keyboards.callback_data import LobbySelectionCallback
from app.services.helpers_module.callback_exceptions import UIErrorHandler as Err
from app.services.helpers_module.dto_helper import FSM_CONTEXT_KEY
from app.services.ui_service.command_service import CommandService
from app.services.ui_service.helpers_ui.ui_tools import await_min_delay
from app.services.ui_service.lobby_service import LobbyService

router = Router(name="login_lobby_router")


@router.callback_query(F.data == "start_adventure")
async def start_login_handler(call: CallbackQuery, state: FSMContext, bot: Bot, session: AsyncSession) -> None:
    """
    Обрабатывает кнопку "Начать приключение".
    Отображает лобби выбора персонажа или запускает процесс создания нового.
    """
    if not call.from_user or not call.message:
        log.warning("Handler 'start_login_handler' received update without 'from_user' or 'message'.")
        return

    user_id = call.from_user.id
    log.info(f"LoginFlow | event=start_adventure user_id={user_id}")
    await call.answer()
    start_time = time.monotonic()

    try:
        com_service = CommandService(call.from_user)
        await com_service.create_user_in_db(session)
        log.debug(f"UserInit | status=checked user_id={user_id}")
    except SQLAlchemyError:
        log.error(f"UserInit | status=db_error user_id={user_id}", exc_info=True)
        await Err.generic_error(call=call)
        return

    lobby_service = LobbyService(user=call.from_user, state_data=await state.get_data())
    character_list = await lobby_service.get_data_characters(session)

    # Исправление: Проверяем character_list перед использованием len()
    characters_count = len(character_list) if character_list is not None else 0
    log.debug(f"LoginFlow | characters_found={characters_count} user_id={user_id}")

    if character_list:  # character_list уже проверен на None выше
        await state.set_state(CharacterLobby.selection)
        await state.update_data({FSM_CONTEXT_KEY: {"user_id": user_id, "char_id": None, "message_content": None}})
        log.info(f"FSM | state=CharacterLobby.selection user_id={user_id}")

        text, kb = lobby_service.get_data_lobby_start(character_list)
        await await_min_delay(start_time, min_delay=0.5)

        if isinstance(call.message, Message):
            await call.message.edit_text(text=text, parse_mode="html", reply_markup=kb)
        log.debug(f"UIRender | component=lobby_menu user_id={user_id}")
    else:
        log.info(f"LoginFlow | reason=no_characters_found action=start_creation user_id={user_id}")
        state_data = await state.get_data()
        session_context = state_data.get(FSM_CONTEXT_KEY, {})
        message_menu: dict[str, Any] | None = session_context.get("message_menu")
        if not message_menu:
            await Err.generic_error(call)
            return

        char_id = await lobby_service.create_and_get_character_id(session)
        if not char_id:
            log.error(f"CharacterCreation | status=failed reason='Could not create character shell' user_id={user_id}")
            await Err.invalid_id(call=call)
            return

        await start_creation_handler(
            call=call,
            state=state,
            user_id=lobby_service.user_id,
            message_menu=message_menu,
            bot=bot,
            char_id=char_id,
            session=session,
        )


@router.callback_query(CharacterLobby.selection, LobbySelectionCallback.filter(F.action == "create"))
async def create_character_handler(call: CallbackQuery, state: FSMContext, bot: Bot, session: AsyncSession) -> None:
    """
    Обрабатывает кнопку "Создать нового персонажа" из лобби.
    """
    if not call.from_user:
        log.warning("Handler 'create_character_handler' received update without 'from_user'.")
        return

    user_id = call.from_user.id
    log.info(f"LoginFlow | event=create_character_from_lobby user_id={user_id}")

    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    message_menu: dict[str, Any] | None = session_context.get("message_menu")
    if not message_menu:
        await Err.generic_error(call)
        return

    lobby_service = LobbyService(user=call.from_user, state_data=state_data)
    char_id = await lobby_service.create_and_get_character_id(session)
    if not char_id:
        log.error(f"CharacterCreation | status=failed reason='Could not create character shell' user_id={user_id}")
        await Err.invalid_id(call=call)
        return

    await start_creation_handler(
        call=call,
        state=state,
        bot=bot,
        user_id=user_id,
        char_id=char_id,
        message_menu=message_menu,
        session=session,
    )
