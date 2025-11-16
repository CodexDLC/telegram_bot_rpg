# app/handlers/callback/login/lobby_character_selection.py
from loguru import logger as log
from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.handlers.callback.ui.status_menu.character_status import show_status_tab_logic
from app.resources.fsm_states.states import CharacterLobby
from app.resources.keyboards.callback_data import LobbySelectionCallback

from app.services.helpers_module.data_loader_service import load_data_auto
from app.services.helpers_module.DTO_helper import fsm_load_auto, fsm_store, fsm_convector
from app.services.helpers_module.callback_exceptions import UIErrorHandler as ERR
from app.services.ui_service.lobbyservice import LobbyService


router = Router(name="lobby_fsm")


@router.callback_query(CharacterLobby.selection, LobbySelectionCallback.filter(F.action == "select"))
async def select_character_handler(
        call: CallbackQuery,
        callback_data: LobbySelectionCallback,
        state: FSMContext,
        bot: Bot
) -> None:
    """
    Обрабатывает выбор персонажа в лобби.

    Загружает данные о персонажах, обновляет список с выделением выбранного,
    отображает подробную информацию о нем и сохраняет состояние в FSM.

    Args:
        call (CallbackQuery): Callback от выбора персонажа.
        state (FSMContext): Состояние FSM.
        bot (Bot): Экземпляр бота.
        callback_data:

    Returns:
        None

    """
    if not call.from_user:
        log.warning("Хэндлер 'select_character_handler' получил обновление без 'from_user'.")
        return

    char_id = callback_data.char_id
    user= call.from_user

    log.info(f"Хэндлер 'select_character_handler' [lobby:select] вызван user_id={user.id}, char_id={char_id}")
    await call.answer()

    # Пытаемся получить список персонажей из FSM.
    characters = await fsm_load_auto(state=state, key="characters")

    # Если в FSM данных нет, загружаем их из БД.
    if characters is None:
        log.info(f"Данные 'characters' для user_id={user.id} не найдены в FSM, загрузка из БД...")
        # 1. Сначала получаем словарь с данными
        loaded_data = await load_data_auto(["characters"], user_id=user.id)
        # 2. Извлекаем из него СПИСОК
        characters_list = loaded_data.get("characters")

        # 3. Сохраняем в FSM, передав fsm_store именно СПИСОК
        await state.update_data(
            characters=await fsm_store(value=characters_list),
        )
        # 4. И не забываем присвоить правильное значение локальной переменной
        characters = characters_list

    if characters:
        state_data = await state.get_data()

        lobby_service = LobbyService(
            user=user,
            char_id=char_id,
            characters= await fsm_convector(characters, "characters")
        )

        text, kb = lobby_service.get_data_lobby_start()

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

        fsm_data = await lobby_service.get_fsm_data()

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
    log.warning(f"Попытка входа в игру (функция-заглушка) для user_id={user_id}, char_id={char_id}. Данные FSM: {state_data}")

    # TODO: Реализовать полную логику входа в игру.
    # TODO: Проверять, пройден ли туториал. Если нет - перенаправлять на него.
    # TODO: Загружать игровое состояние (локация, инвентарь и т.д.).
    # TODO: Очищать сообщение лобби и меню, создавать игровой интерфейс.



@router.callback_query(CharacterLobby.selection, LobbySelectionCallback.filter(F.action == "delete"))
async def delete_character_lobby(call: CallbackQuery, state: FSMContext):
    pass