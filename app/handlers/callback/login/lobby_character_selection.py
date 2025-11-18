# app/handlers/callback/login/lobby_character_selection.py
from typing import Any

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger as log

from app.handlers.callback.ui.status_menu.character_status import show_status_tab_logic
from app.resources.fsm_states.states import CharacterLobby, InGame
from app.resources.keyboards.callback_data import LobbySelectionCallback
from app.resources.texts.ui_messages import TEXT_AWAIT
from app.services.game_service.login_service import LoginService
from app.services.helpers_module.callback_exceptions import UIErrorHandler as Err
from app.services.helpers_module.dto_helper import fsm_clean_core_state, fsm_load_auto, fsm_store
from app.services.ui_service.lobby_service import LobbyService
from app.services.ui_service.menu_service import MenuService
from app.services.ui_service.navigation_service import NavigationService

router = Router(name="lobby_fsm")


# 1. ДЕКОРАТОР ТЕПЕРЬ ЛОВИТ СПИСОК {"select", "delete"}
@router.callback_query(CharacterLobby.selection, LobbySelectionCallback.filter(F.action.in_({"select", "delete"})))
async def select_or_delete_character_handler(
    call: CallbackQuery, callback_data: LobbySelectionCallback, state: FSMContext, bot: Bot
) -> None:
    """
    Обрабатывает ВЫБОР или УДАЛЕНИЕ персонажа в лобби.

    При 'select': Загружает данные, обновляет список, показывает статус.
    При 'delete': Запрашивает подтверждение на удаление (пока заглушка).

    Args:
        call (CallbackQuery): Callback от выбора персонажа.
        state (FSMContext): Состояние FSM.
        bot (Bot): Экземпляр бота.
        callback_data:

    Returns:
        None
    """
    if not call.from_user:
        log.warning("Хэндлер 'select_or_delete_character_handler' получил обновление без 'from_user'.")
        return

    # --- 2. ОБЩИЙ БЛОК: Загрузка данных (нужен для обоих) ---
    char_id = callback_data.char_id
    user = call.from_user
    action = callback_data.action

    log.info(
        f"Хэндлер 'select_or_delete_character_handler' [lobby:{action}] вызван user_id={user.id}, char_id={char_id}"
    )

    # Отвечаем на call сразу (важно для delete, чтобы убрать часики)
    await call.answer()
    state_data = await state.get_data()

    current_char_id_in_fsm = state_data.get("char_id")
    if action == "select" and char_id == current_char_id_in_fsm:
        log.debug(f"User {user.id} повторно нажал на уже выбранного персонажа {char_id}. Игнорируем.")
        return

    # Инициализируем сервис
    lobby_service = LobbyService(user=user, char_id=char_id, state_data=state_data)

    # Пытаемся получить список персонажей из FSM.
    characters = await fsm_load_auto(state=state, key="characters")

    # Если в FSM данных нет, загружаем их из БД.
    if characters is None:
        log.info(f"Данные 'characters' для user_id={user.id} не найдены в FSM, загрузка из БД...")
        characters = await lobby_service.get_data_characters()
        # Сохраняем в FSM
        if characters:
            await state.update_data(characters=await fsm_store(value=characters))

    # --- 3. РАЗДЕЛЕНИЕ ЛОГИКИ (if/elif) ---

    if action == "select":
        if not char_id:
            await Err.generic_error(call=call)
            return
        # --- 4. ЛОГИКА "SELECT" (твой готовый код) ---
        if characters:
            text, kb = lobby_service.get_data_lobby_start(characters)

            message_menu: dict[str, Any] | None = state_data.get("message_menu")
            log.debug(f"message_menu = {message_menu} ")

            if message_menu:
                await bot.edit_message_text(
                    chat_id=message_menu.get("chat_id"),
                    message_id=message_menu.get("message_id"),
                    text=text,
                    parse_mode="html",
                    reply_markup=kb,
                )

            # (Исправленный вызов, как мы обсуждали)
            fsm_data = await lobby_service.get_fsm_data(characters)

            # Сохраняем ID выбранного персонажа.
            await state.update_data(**fsm_data)

            # Вызываем обработчик меню статуса для отображения информации.
            await show_status_tab_logic(char_id=char_id, state=state, bot=bot, call=call, key="bio")
        else:
            log.warning(f"У user_id={user.id} нет персонажей, хотя он находится в лобби выбора.")
            await Err.generic_error(call=call)

    elif action == "delete":
        # --- 5. ЛОГИКА "DELETE" (новая) ---
        log.debug(f"Запрос на удаление [lobby:delete] для char_id={char_id}.")

        # Проверяем, что персонаж вообще выбран
        if not char_id:
            log.warning(f"User {user.id} нажал 'delete', не выбрав персонажа.")
            await call.answer("Сначала выберите персонажа, которого хотите удалить", show_alert=True)
            return

            # 1. Получаем message_content (где висит статус)
        message_content = state_data.get("message_content")

        if not isinstance(message_content, dict):
            log.error(f"User {user.id}: Не найден 'message_content' для показа подтверждения удаления.")
            await Err.message_content_not_found_in_fsm(call)
            return

        char_name = "???"
        if characters:
            for char in characters:
                if char.character_id == char_id:
                    char_name = char.name
                    break

        await state.set_state(CharacterLobby.confirm_delete)

        text, kb = lobby_service.get_message_delete(char_name)

        await state.update_data(char_name=char_name)

        chat_id, message_id = lobby_service.get_message_content_data()
        if chat_id and message_id:
            await bot.edit_message_text(
                chat_id=chat_id, message_id=message_id, text=text, parse_mode="html", reply_markup=kb
            )


@router.callback_query(CharacterLobby.confirm_delete, LobbySelectionCallback.filter())
async def confirm_delete_handler(
    call: CallbackQuery, state: FSMContext, callback_data: LobbySelectionCallback, bot: Bot
) -> None:
    """
    Обрабатывает подтверждение ("Да") или отмену ("Нет") удаления персонажа.
    """

    if not call.from_user or not call.message:
        log.warning("Хэндлер 'confirm_delete_handler' получил обновление без 'from_user' или 'message'.")
        return

    await call.answer()  # Отвечаем на call в любом случае

    state_data = await state.get_data()
    # char_id для "Нет" берем из callback, для "Да" - лучше из state
    char_id = callback_data.char_id or state_data.get("char_id")
    user = call.from_user

    if not char_id:
        log.error(f"User {user.id}: Не найден char_id в confirm_delete_handler.")
        await Err.generic_error(call)
        return

    lobby_service = LobbyService(user=user, char_id=char_id, state_data=state_data)

    if callback_data.action == "delete_yes":
        log.info("Хэндлер 'confirm_delete_handler' [lobby:delete_yes] вызван")

        await lobby_service.delete_character_ind_db()
        char_name = state_data.get("char_name")
        text = f"персонаж {char_name} удален"
        if isinstance(call.message, Message):
            await call.message.edit_text(text=text, reply_markup=None)
        characters = await lobby_service.get_data_characters()
        text, kb = lobby_service.get_data_lobby_start(characters)
        message_menu_data = lobby_service.get_message_menu_data()
        if message_menu_data:
            chat_id, message_id = message_menu_data
            if chat_id and message_id:
                await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=kb)
        await state.set_state(CharacterLobby.selection)

    elif callback_data.action == "delete_no":
        log.info(f"User {user.id} отменил удаление персонажа {char_id}.")

        # 1. Возвращаем стейт в лобби
        await state.set_state(CharacterLobby.selection)

        # 2. Восстанавливаем НИЖНЕЕ сообщение (message_content),
        #    показывая "Био" персонажа, как и было.
        await show_status_tab_logic(
            char_id=char_id,
            state=state,
            bot=bot,
            call=call,  # `show_status_tab_logic` сам возьмет `call.message`
            key="bio",
        )


@router.callback_query(CharacterLobby.selection, LobbySelectionCallback.filter(F.action == "login"))
async def start_logging_handler(call: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    """
    Обрабатывает нажатие кнопки "Войти в игру".
    (Правильная версия, по твоей архитектуре)
    """
    if not call.from_user:
        log.warning("Хэндлер 'start_logging_handler' получил обновление без 'from_user'.")
        return

    # --- 1. Сбор данных и показ заглушки ---
    user_id = call.from_user.id
    state_data = await state.get_data()
    char_id = state_data.get("char_id")
    message_menu: dict[str, Any] | None = state_data.get("message_menu")
    message_content: dict[str, Any] | None = state_data.get("message_content")  # <-- Нам нужны ОБА

    if not isinstance(char_id, int) or not isinstance(message_menu, dict) or not isinstance(message_content, dict):
        log.error(f"User {call.from_user.id} нажал 'login', но FSM неполный.")
        await Err.generic_error(call)
        return

    log.info(f"Хэндлер 'start_logging_handler' [lobby:login] вызван user_id={call.from_user.id}, char_id={char_id}")

    # Ставим заглушки на ОБА сообщения
    await bot.edit_message_text(
        chat_id=message_menu["chat_id"], message_id=message_menu["message_id"], text=TEXT_AWAIT, reply_markup=None
    )
    await bot.edit_message_text(
        chat_id=message_content["chat_id"],
        message_id=message_content["message_id"],
        text=TEXT_AWAIT,
        reply_markup=None,
    )

    # --- 2. Вызываем LoginService (Бизнес-логика) ---
    login_service = LoginService(char_id=char_id, state_data=state_data)
    login_result = await login_service.handle_login()

    # --- 3. Проверяем результат (Твоя логика редиректа) ---
    if not login_result or (isinstance(login_result, tuple) and login_result[0] not in ("world", "s_d")):
        game_stage = login_result[0] if isinstance(login_result, tuple) else "unknown"
        log.info(f"Редирект: char_id={char_id} не 'in_game'. Stage: {game_stage}")

        # TODO: логика для перевода игрока в туториал
        # ... await redirect_to_tutorial_stats(call, state, bot, char_id) ...
        await call.answer(f"Вход невозможен. Сначала завершите этап: {game_stage}", show_alert=True)
        # (Тут нужно вернуть UI лобби, но пока просто прерываем)
        return

    if not isinstance(login_result, tuple):
        await Err.generic_error(call)
        return
    # --- 4. Логин УСПЕШЕН. Получаем ДАННЫЕ ---
    state_name, loc_id = login_result
    log.info(f"Логин для char_id={char_id} успешен. Вход в: {state_name}:{loc_id}")

    # --- 5. Вызываем Сервисы для UI ---
    nav_service = NavigationService(char_id=char_id, state_data=state_data)
    nav_text, nav_kb = await nav_service.get_navigation_ui(state_name, loc_id)  # (UI для низа)

    menu_service = MenuService(game_stage="in_game", char_id=char_id)
    menu_text, menu_kb = menu_service.get_data_menu()  # (UI для верха)

    # --- 6. Перестраиваем UI (Правильный способ) ---

    # A. Редактируем ВЕРХНЕЕ сообщение (`message_menu`)
    await bot.edit_message_text(
        chat_id=message_menu["chat_id"],
        message_id=message_menu["message_id"],
        text=menu_text,
        reply_markup=menu_kb,
        parse_mode="HTML",
    )

    # Б. Редактируем НИЖНЕЕ сообщение (`message_content`)
    await bot.edit_message_text(
        chat_id=message_content["chat_id"],
        message_id=message_content["message_id"],
        text=nav_text,
        reply_markup=nav_kb,
        parse_mode="HTML",
    )

    # --- 7. Обновляем FSM ---

    # Сначала ОЧИЩАЕМ FSM от мусора, сохраняя только ядро
    await fsm_clean_core_state(state=state, event_source=call)

    # А потом УСТАНАВЛИВАЕМ новый стейт
    await state.set_state(InGame.navigation)

    log.info(f"User {user_id} (char_id={char_id}) вошел в мир. FSM: InGame.navigation.")
