# app/handlers/callback/login/lobby_character_selection.py
from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from app.handlers.callback.ui.status_menu.character_status import show_status_tab_logic
from app.resources.fsm_states.states import CharacterLobby
from app.resources.keyboards.callback_data import LobbySelectionCallback
from app.services.helpers_module.callback_exceptions import UIErrorHandler as Err
from app.services.helpers_module.dto_helper import (
    FSM_CONTEXT_KEY,
    fsm_load_auto,
    fsm_store,
)
from app.services.ui_service.lobby_service import LobbyService

router = Router(name="lobby_selection_router")


@router.callback_query(CharacterLobby.selection, LobbySelectionCallback.filter(F.action.in_({"select", "delete"})))
async def select_or_delete_character_handler(
    call: CallbackQuery,
    callback_data: LobbySelectionCallback,
    state: FSMContext,
    bot: Bot,
    session: AsyncSession,
) -> None:
    """
    Обрабатывает выбор или удаление персонажа в лобби.

    Args:
        call (CallbackQuery): Входящий колбэк.
        callback_data (LobbySelectionCallback): Данные колбэка.
        state (FSMContext): Контекст FSM.
        bot (Bot): Экземпляр бота.
        session (AsyncSession): Сессия базы данных.

    Returns:
        None
    """
    if not call.from_user:
        log.warning("Колбэк без `from_user` в 'select_or_delete_character_handler'.")
        return

    char_id = callback_data.char_id
    user = call.from_user
    action = callback_data.action

    log.info(
        f"Хэндлер 'select_or_delete_character_handler' [action:{action}] вызван user_id={user.id}, char_id={char_id}"
    )

    await call.answer()
    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})

    # Предотвращение повторной обработки того же выбора
    current_char_id_in_fsm = session_context.get("char_id")
    if action == "select" and char_id == current_char_id_in_fsm:
        log.debug(f"Пользователь {user.id} повторно выбрал того же персонажа {char_id}.")
        return

    lobby_service = LobbyService(user=user, char_id=char_id, state_data=state_data)
    characters = await fsm_load_auto(state=state, key="characters")

    # Если персонажи не в FSM, загружаем из БД
    if characters is None:
        log.debug(f"Персонажи не найдены в FSM для user_id={user.id}, загрузка из БД.")
        characters = await lobby_service.get_data_characters(session)
        if characters:
            await state.update_data(characters=await fsm_store(value=characters))

    if action == "select":
        if not char_id:
            log.warning(f"User {user.id} попытался выбрать персонажа, но char_id is None.")
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

            # Обновление FSM с данными выбранного персонажа
            fsm_data = await lobby_service.get_fsm_data(characters)
            current_data = await state.get_data()
            session_context = current_data.get(FSM_CONTEXT_KEY, {})
            session_context["char_id"] = fsm_data.get("char_id")
            session_context["user_id"] = fsm_data.get("user_id")
            await state.update_data({FSM_CONTEXT_KEY: session_context})
            await state.update_data(characters=fsm_data.get("characters"))
            log.debug(f"Данные FSM обновлены для user_id={user.id}, char_id={char_id}")

            # Показываем первую вкладку статуса персонажа
            await show_status_tab_logic(
                char_id=char_id,
                state=state,
                bot=bot,
                call=call,
                key="bio",
                session=session,
            )
        else:
            log.warning(f"Не найдены персонажи для user_id={user.id} после выбора.")
            await Err.generic_error(call=call)

    elif action == "delete":
        if not char_id:
            log.warning(
                f"User {user.id} в 'select_or_delete_character_handler' попытался удалить персонажа, но char_id=None."
            )
            await call.answer("Сначала выберите персонажа, которого хотите удалить", show_alert=True)
            return

        message_content = session_context.get("message_content")
        if not isinstance(message_content, dict):
            log.warning(f"User {user.id} в 'select_or_delete_character_handler' не имеет 'message_content' в FSM.")
            await Err.message_content_not_found_in_fsm(call)
            return

        # Получаем имя персонажа для сообщения подтверждения
        char_name = "???"
        if characters:
            for char in characters:
                if char.character_id == char_id:
                    char_name = char.name
                    break

        await state.set_state(CharacterLobby.confirm_delete)
        text, kb = lobby_service.get_message_delete(char_name)
        await state.update_data(char_name=char_name)
        log.debug(
            f"Состояние FSM для user_id={user.id} установлено в CharacterLobby.confirm_delete для char_id={char_id}"
        )

        message_content_data = lobby_service.get_message_content_data()
        if message_content_data is None:
            await Err.message_content_not_found_in_fsm(call)
            return

        chat_id, message_id = message_content_data
        if chat_id and message_id:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                parse_mode="html",
                reply_markup=kb,
            )


@router.callback_query(CharacterLobby.confirm_delete, LobbySelectionCallback.filter())
async def confirm_delete_handler(
    call: CallbackQuery,
    state: FSMContext,
    callback_data: LobbySelectionCallback,
    bot: Bot,
    session: AsyncSession,
) -> None:
    """
    Обрабатывает подтверждение или отмену удаления персонажа.

    Args:
        call (CallbackQuery): Входящий колбэк.
        state (FSMContext): Контекст FSM.
        callback_data (LobbySelectionCallback): Данные колбэка.
        bot (Bot): Экземпляр бота.
        session (AsyncSession): Сессия базы данных.

    Returns:
        None
    """
    if not call.from_user or not call.message:
        log.warning("Колбэк без `from_user` или `message` в 'confirm_delete_handler'.")
        return

    await call.answer()
    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    # char_id берется из callback_data, если его там нет - из контекста FSM
    char_id = callback_data.char_id or session_context.get("char_id")
    user = call.from_user
    action = callback_data.action

    log.info(f"Хэндлер 'confirm_delete_handler' [action:{action}] вызван user_id={user.id}, char_id={char_id}")

    if not char_id:
        log.warning(f"User {user.id} в 'confirm_delete_handler' не имеет char_id.")
        await Err.generic_error(call)
        return

    lobby_service = LobbyService(user=user, char_id=char_id, state_data=state_data)

    if action == "delete_yes":
        log.debug(f"Пользователь {user.id} подтвердил удаление персонажа {char_id}.")
        delete_success = await lobby_service.delete_character(session)

        if not delete_success:
            log.error(f"Не удалось удалить персонажа {char_id} для user_id={user.id}.")
            await Err.generic_error(call)
            return

        # Обновляем список персонажей после удаления
        characters = await lobby_service.get_data_characters(session)
        await state.update_data(characters=await fsm_store(value=characters))
        log.debug(f"Список персонажей для user_id={user.id} обновлен в FSM.")

        # Обновляем оба сообщения: меню и контент
        text_lobby, kb_lobby = lobby_service.get_data_lobby_start(characters)
        message_menu_data = lobby_service.get_message_menu_data()
        if message_menu_data:
            chat_id, message_id = message_menu_data
            if chat_id and message_id:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=text_lobby,
                    reply_markup=kb_lobby,
                )

        message_content_data = lobby_service.get_message_content_data()
        if message_content_data:
            chat_id, message_id = message_content_data
            if chat_id and message_id:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text="Персонаж удален. Выберите другого персонажа или создайте нового.",
                    reply_markup=None,
                )

        # Сбрасываем char_id в FSM и возвращаемся к выбору
        session_context["char_id"] = None
        await state.update_data({FSM_CONTEXT_KEY: session_context})
        await state.set_state(CharacterLobby.selection)
        log.debug(f"char_id сброшен в FSM. Состояние установлено в CharacterLobby.selection для user_id={user.id}.")

    elif action == "delete_no":
        log.debug(f"Пользователь {user.id} отменил удаление персонажа {char_id}.")
        await state.set_state(CharacterLobby.selection)
        # Возвращаем пользователя к просмотру статуса персонажа
        await show_status_tab_logic(
            char_id=char_id,
            state=state,
            bot=bot,
            call=call,
            key="bio",
            session=session,
        )
