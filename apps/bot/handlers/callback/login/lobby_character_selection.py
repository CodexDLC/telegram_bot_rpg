from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from apps.bot.handlers.callback.ui.status_menu.character_status import show_status_tab_logic
from apps.bot.resources.fsm_states.states import CharacterLobby
from apps.bot.resources.keyboards.callback_data import LobbySelectionCallback
from apps.bot.ui_service.helpers_ui.callback_exceptions import UIErrorHandler as Err
from apps.bot.ui_service.helpers_ui.dto_helper import FSM_CONTEXT_KEY, fsm_load_auto, fsm_store
from apps.bot.ui_service.lobby_service import LobbyService

router = Router(name="lobby_selection_router")


@router.callback_query(CharacterLobby.selection, LobbySelectionCallback.filter(F.action.in_({"select", "delete"})))
async def select_or_delete_character_handler(
    call: CallbackQuery,
    callback_data: LobbySelectionCallback,
    state: FSMContext,
    bot: Bot,
    session: AsyncSession,
) -> None:
    """Обрабатывает выбор или удаление персонажа в лобби."""
    if not call.from_user:
        return

    char_id = callback_data.char_id
    user_id = call.from_user.id
    action = callback_data.action
    log.info(f"Lobby | action={action} user_id={user_id} char_id={char_id}")

    await call.answer()
    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})

    current_char_id_in_fsm = session_context.get("char_id")
    if action == "select" and char_id == current_char_id_in_fsm:
        log.debug(f"Lobby | reason='repeated_selection' user_id={user_id} char_id={char_id}")
        return

    lobby_service = LobbyService(user=call.from_user, char_id=char_id, state_data=state_data)
    characters = await fsm_load_auto(state=state, key="characters")

    if characters is None:
        log.debug(f"Lobby | cache=miss key=characters user_id={user_id}")
        characters = await lobby_service.get_data_characters(session)
        if characters:
            await state.update_data(characters=await fsm_store(value=characters))

    if action == "select":
        if not char_id:
            log.warning(f"Lobby | action=select status=failed reason='char_id is None' user_id={user_id}")
            await Err.generic_error(call=call)
            return

        if characters:
            text, kb = lobby_service.get_data_lobby_start(characters)
            message_menu = session_context.get("message_menu")
            if message_menu:
                await bot.edit_message_text(
                    chat_id=message_menu.get("chat_id"),
                    message_id=message_menu.get("message_id"),
                    text=text,
                    parse_mode="html",
                    reply_markup=kb,
                )

            fsm_data = await lobby_service.get_fsm_data(characters)
            session_context.update({"char_id": fsm_data.get("char_id"), "user_id": fsm_data.get("user_id")})
            await state.update_data({FSM_CONTEXT_KEY: session_context})
            await state.update_data(characters=fsm_data.get("characters"))
            log.debug(f"FSM | data_updated user_id={user_id} char_id={char_id}")

            await show_status_tab_logic(char_id=char_id, state=state, bot=bot, call=call, key="bio", session=session)
        else:
            log.warning(f"Lobby | status=failed reason='characters not found after selection' user_id={user_id}")
            await Err.generic_error(call=call)

    elif action == "delete":
        if not char_id:
            log.warning(f"Lobby | action=delete status=failed reason='char_id is None' user_id={user_id}")
            await call.answer("Сначала выберите персонажа, которого хотите удалить", show_alert=True)
            return

        message_content = session_context.get("message_content")
        if not isinstance(message_content, dict):
            log.warning(f"Lobby | status=failed reason='message_content not found' user_id={user_id}")
            await Err.message_content_not_found_in_fsm(call)
            return

        char_name = next((char.name for char in characters if char.character_id == char_id), "???")

        await state.set_state(CharacterLobby.confirm_delete)
        text, kb = lobby_service.get_message_delete(char_name)
        await state.update_data(char_name=char_name)
        log.info(f"FSM | state=CharacterLobby.confirm_delete user_id={user_id} char_id={char_id}")

        message_content_data = lobby_service.get_message_content_data()
        if message_content_data:
            chat_id, message_id = message_content_data
            await bot.edit_message_text(
                chat_id=chat_id, message_id=message_id, text=text, parse_mode="html", reply_markup=kb
            )
        else:
            await Err.message_content_not_found_in_fsm(call)


@router.callback_query(CharacterLobby.confirm_delete, LobbySelectionCallback.filter())
async def confirm_delete_handler(
    call: CallbackQuery, state: FSMContext, callback_data: LobbySelectionCallback, bot: Bot, session: AsyncSession
) -> None:
    """Обрабатывает подтверждение или отмену удаления персонажа."""
    if not call.from_user or not call.message:
        return

    await call.answer()
    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    char_id = callback_data.char_id or session_context.get("char_id")
    user_id = call.from_user.id
    action = callback_data.action
    log.info(f"LobbyDeleteConfirm | action={action} user_id={user_id} char_id={char_id}")

    if not char_id:
        log.warning(f"LobbyDeleteConfirm | status=failed reason='char_id is None' user_id={user_id}")
        await Err.generic_error(call)
        return

    lobby_service = LobbyService(user=call.from_user, char_id=char_id, state_data=state_data)

    if action == "delete_yes":
        log.debug(f"LobbyDeleteConfirm | status=confirmed user_id={user_id} char_id={char_id}")
        delete_success = await lobby_service.delete_character(session)

        if not delete_success:
            log.error(f"DBDelete | entity=character status=failed char_id={char_id} user_id={user_id}")
            await Err.generic_error(call)
            return

        characters = await lobby_service.get_data_characters(session)
        await state.update_data(characters=await fsm_store(value=characters))
        log.debug(f"FSM | data_updated key=characters user_id={user_id}")

        text_lobby, kb_lobby = lobby_service.get_data_lobby_start(characters)
        if message_menu_data := lobby_service.get_message_menu_data():
            await bot.edit_message_text(
                chat_id=message_menu_data[0], message_id=message_menu_data[1], text=text_lobby, reply_markup=kb_lobby
            )
        if message_content_data := lobby_service.get_message_content_data():
            await bot.edit_message_text(
                chat_id=message_content_data[0],
                message_id=message_content_data[1],
                text="Персонаж удален. Выберите другого персонажа или создайте нового.",
                reply_markup=None,
            )

        session_context["char_id"] = None
        await state.update_data({FSM_CONTEXT_KEY: session_context})
        await state.set_state(CharacterLobby.selection)
        log.info(f"FSM | state=CharacterLobby.selection reason=delete_confirmed user_id={user_id}")

    elif action == "delete_no":
        log.debug(f"LobbyDeleteConfirm | status=cancelled user_id={user_id} char_id={char_id}")
        await state.set_state(CharacterLobby.selection)
        await show_status_tab_logic(char_id=char_id, state=state, bot=bot, call=call, key="bio", session=session)
