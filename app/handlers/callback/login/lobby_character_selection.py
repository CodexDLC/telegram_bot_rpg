# app/handlers/callback/login/lobby_character_selection.py
from loguru import logger as log
from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.handlers.callback.ui.status_menu.character_status import show_status_tab_logic
from app.resources.fsm_states.states import CharacterLobby
from app.resources.keyboards.callback_data import LobbySelectionCallback

from app.services.helpers_module.DTO_helper import fsm_load_auto, fsm_store, fsm_convector
from app.services.helpers_module.callback_exceptions import UIErrorHandler as ERR
from app.services.ui_service.lobby_service import LobbyService

router = Router(name="lobby_fsm")


# 1. ДЕКОРАТОР ТЕПЕРЬ ЛОВИТ СПИСОК {"select", "delete"}
@router.callback_query(CharacterLobby.selection, LobbySelectionCallback.filter(F.action.in_({"select", "delete"})))
async def select_or_delete_character_handler(
        call: CallbackQuery,
        callback_data: LobbySelectionCallback,
        state: FSMContext,
        bot: Bot
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
        f"Хэндлер 'select_or_delete_character_handler' [lobby:{action}] вызван user_id={user.id}, char_id={char_id}")

    # Отвечаем на call сразу (важно для delete, чтобы убрать часики)
    await call.answer()
    state_data = await state.get_data()

    current_char_id_in_fsm = state_data.get("char_id")
    if action == "select" and char_id == current_char_id_in_fsm:
        log.debug(f"User {user.id} повторно нажал на уже выбранного персонажа {char_id}. Игнорируем.")
        return

    # Инициализируем сервис
    lobby_service = LobbyService(
        user=user,
        char_id=char_id,
        state_data=state_data
    )

    # Пытаемся получить список персонажей из FSM.
    characters = await fsm_load_auto(state=state, key="characters")

    # Если в FSM данных нет, загружаем их из БД.
    if characters is None:
        log.info(f"Данные 'characters' для user_id={user.id} не найдены в FSM, загрузка из БД...")
        characters = await lobby_service.get_data_characters()
        # Сохраняем в FSM
        await state.update_data(characters=await fsm_store(value=characters))

    # --- 3. РАЗДЕЛЕНИЕ ЛОГИКИ (if/elif) ---

    if action == "select":
        # --- 4. ЛОГИКА "SELECT" (твой готовый код) ---
        if characters:
            text, kb = lobby_service.get_data_lobby_start(characters)

            message_menu = state_data.get("message_menu")
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
            await show_status_tab_logic(
                char_id=char_id,
                state=state,
                bot=bot,
                call=call,
                key="bio"
            )
        else:
            log.warning(f"У user_id={user.id} нет персонажей, хотя он находится в лобби выбора.")
            await ERR.generic_error(call=call)

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

        if not message_content:
            log.error(f"User {user.id}: Не найден 'message_content' для показа подтверждения удаления.")
            await ERR.message_content_not_found_in_fsm(call)
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
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            parse_mode="html",
            reply_markup=kb
        )


@router.callback_query(CharacterLobby.confirm_delete, LobbySelectionCallback.filter())
async def confirm_delete_handler(call: CallbackQuery, state: FSMContext, callback_data: LobbySelectionCallback, bot: Bot) -> None:
    """
        Обрабатывает подтверждение ("Да") или отмену ("Нет") удаления персонажа.
        """

    if not call.from_user:
        log.warning("Хэндлер 'confirm_delete_handler' получил обновление без 'from_user'.")
        return

    await call.answer()  # Отвечаем на call в любом случае

    state_data = await state.get_data()
    # char_id для "Нет" берем из callback, для "Да" - лучше из state
    char_id = callback_data.char_id or state_data.get("char_id")
    user = call.from_user

    if not char_id:
        log.error(f"User {user.id}: Не найден char_id в confirm_delete_handler.")
        await ERR.generic_error(call)
        return

    lobby_service = LobbyService(
        user=user,
        char_id=char_id,
        state_data=state_data
    )

    if callback_data.action == "delete_yes":
        log.info(f"Хэндлер 'confirm_delete_handler' [lobby:delete_yes] вызван")

        await lobby_service.delete_character_ind_db()
        char_name = state_data.get("char_name")
        text = f"персонаж {char_name} удален"
        await call.message.edit_text(text=text, reply_markup=None)
        characters = await lobby_service.get_data_characters()
        text, kb = lobby_service.get_data_lobby_start(characters)
        chat_id, message_id = lobby_service.get_message_menu_data()
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
            key="bio"
        )




@router.callback_query(CharacterLobby.selection, LobbySelectionCallback.filter(F.action == "login"))
async def start_logging_handler(call: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    """
    Обрабатывает нажатие кнопки "Войти в игру" (заглушка).

    Args:
        call (CallbackQuery): Callback от кнопки "Войти в игру".
        state (FSMContext): Состояние FSM.
        bot (Bot): Экземпляр бота.

    Returns:
        None
    """
    if not call.from_user:
        log.warning("Хэндлер 'start_logging_handler' получил обновление без 'from_user'.")
        return

    user_id = call.from_user.id
    state_data = await state.get_data()
    char_id = state_data.get("char_id")

    log.info(f"Хэндлер 'start_logging_handler' [lobby:login] вызван user_id={user_id}, char_id={char_id}")
    await call.answer(text="⚠️ Функция входа в игру находится в разработке.", show_alert=True)
    log.warning(
        f"Попытка входа в игру (функция-заглушка) для user_id={user_id}, char_id={char_id}. Данные FSM: {state_data}")

    # TODO: Реализовать полную логику входа в игру.
    # TODO: Проверять, пройден ли туториал. Если нет - перенаправлять на него.
    # TODO: Загружать игровое состояние (локация, инвентарь и т.д.).
    # TODO: Очищать сообщение лобби и меню, создавать игровой интерфейс.







