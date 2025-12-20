from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from apps.bot.handlers.callback.ui.status_menu.character_status import show_status_tab_logic
from apps.bot.resources.fsm_states.states import CharacterLobby
from apps.bot.resources.keyboards.callback_data import LobbySelectionCallback
from apps.bot.ui_service.helpers_ui.callback_exceptions import UIErrorHandler as Err
from apps.bot.ui_service.helpers_ui.dto_helper import FSM_CONTEXT_KEY
from apps.common.core.container import AppContainer

router = Router(name="lobby_selection_router")


@router.callback_query(CharacterLobby.selection, LobbySelectionCallback.filter(F.action.in_({"select", "delete"})))
async def select_or_delete_character_handler(
    call: CallbackQuery,
    callback_data: LobbySelectionCallback,
    state: FSMContext,
    bot: Bot,
    session: AsyncSession,
    container: AppContainer,
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

    # Создаем оркестратор через контейнер
    orchestrator = container.get_lobby_bot_orchestrator(session)

    if action == "select":
        if not char_id:
            log.warning(f"Lobby | action=select status=failed reason='char_id is None' user_id={user_id}")
            await Err.generic_error(call=call)
            return

        # Получаем вид лобби (список персонажей)
        result_dto = await orchestrator.get_lobby_view(call.from_user, state_data, char_id)

        # Обновляем меню (список персонажей)
        if result_dto.content and (coords := orchestrator.get_menu_coords(state_data)):
            await bot.edit_message_text(
                chat_id=coords.chat_id,
                message_id=coords.message_id,
                text=result_dto.content.text,
                parse_mode="html",
                reply_markup=result_dto.content.kb,
            )

        # Обновляем FSM
        session_context.update({"char_id": char_id, "user_id": user_id})
        await state.update_data({FSM_CONTEXT_KEY: session_context})
        log.debug(f"FSM | data_updated user_id={user_id} char_id={char_id}")

        # Показываем статус персонажа (через мост)
        await show_status_tab_logic(
            char_id=char_id, state=state, bot=bot, call=call, key="bio", session=session, container=container
        )

    elif action == "delete":
        if not char_id:
            log.warning(f"Lobby | action=delete status=failed reason='char_id is None' user_id={user_id}")
            await call.answer("Сначала выберите персонажа, которого хотите удалить", show_alert=True)
            return

        await state.set_state(CharacterLobby.confirm_delete)

        # Получаем экран подтверждения удаления
        result_dto = await orchestrator.get_delete_confirmation(call.from_user, state_data, char_id)

        # Обновляем контент (верхнее сообщение)
        if result_dto.content and (coords := orchestrator.get_content_coords(state_data)):
            await bot.edit_message_text(
                chat_id=coords.chat_id,
                message_id=coords.message_id,
                text=result_dto.content.text,
                parse_mode="html",
                reply_markup=result_dto.content.kb,
            )
        else:
            await Err.message_content_not_found_in_fsm(call)


@router.callback_query(CharacterLobby.confirm_delete, LobbySelectionCallback.filter())
async def confirm_delete_handler(
    call: CallbackQuery,
    state: FSMContext,
    callback_data: LobbySelectionCallback,
    bot: Bot,
    session: AsyncSession,
    container: AppContainer,
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

    orchestrator = container.get_lobby_bot_orchestrator(session)

    if action == "delete_yes":
        log.debug(f"LobbyDeleteConfirm | status=confirmed user_id={user_id} char_id={char_id}")

        # Удаляем персонажа через оркестратор
        result_dto = await orchestrator.delete_character(char_id)

        if not result_dto.is_deleted:
            log.error(f"DBDelete | entity=character status=failed char_id={char_id} user_id={user_id}")
            await Err.generic_error(call)
            return

        # Обновляем лобби (список персонажей)
        lobby_view = await orchestrator.get_lobby_view(call.from_user, state_data)

        if lobby_view.content and (coords := orchestrator.get_menu_coords(state_data)):
            await bot.edit_message_text(
                chat_id=coords.chat_id,
                message_id=coords.message_id,
                text=lobby_view.content.text,
                reply_markup=lobby_view.content.kb,
            )

        if coords := orchestrator.get_content_coords(state_data):
            await bot.edit_message_text(
                chat_id=coords.chat_id,
                message_id=coords.message_id,
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
        await show_status_tab_logic(
            char_id=char_id, state=state, bot=bot, call=call, key="bio", session=session, container=container
        )
