# app/handlers/callback/login/lobby_character_selection.py
import logging
from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.handlers.callback.ui.status_menu.character_status import status_menu_start_handler
from app.resources.fsm_states.states import CharacterLobby

from app.services.helpers_module.data_loader_service import load_data_auto
from app.services.helpers_module.DTO_helper import fsm_load_auto, fsm_store
from app.services.ui_service.helpers_ui.lobby_formatters import LobbyFormatter
from app.services.helpers_module.callback_exceptions import UIErrorHandler as ERR

log = logging.getLogger(__name__)

router = Router(name="lobby_fsm")


@router.callback_query(CharacterLobby.selection, F.data.startswith("lobby:select"))
async def select_character_handler(call: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    """
    Обрабатывает выбор персонажа в лобби.

    Загружает данные о персонажах, обновляет список с выделением выбранного,
    отображает подробную информацию о нем и сохраняет состояние в FSM.

    Args:
        call (CallbackQuery): Callback от выбора персонажа.
        state (FSMContext): Состояние FSM.
        bot (Bot): Экземпляр бота.

    Returns:
        None
    """
    if not call.from_user:
        log.warning("Хэндлер 'select_character_handler' получил обновление без 'from_user'.")
        return

    char_id = int(call.data.split(":")[-1])
    user = call.from_user
    user_id= user.id
    log.info(f"Хэндлер 'select_character_handler' [lobby:select] вызван user_id={user_id}, char_id={char_id}")
    await call.answer()

    # Пытаемся получить список персонажей из FSM.
    characters = await fsm_load_auto(state=state, key="characters")

    # Если в FSM данных нет, загружаем их из БД.
    if characters is None:
        log.info(f"Данные 'characters' для user_id={user_id} не найдены в FSM, загрузка из БД...")
        get_data = await load_data_auto(
            ["characters", "character_stats"],
            character_id=char_id,
            user_id=user_id,
        )
        characters = get_data.get("characters")
        # Сохраняем полученные данные в FSM.
        await state.update_data(
            characters=await fsm_store(value=characters),
            character_stats=await fsm_store(value=get_data.get("character_stats"))
        )
        log.debug(f"Данные 'characters' и 'character_stats' для user_id={user_id} загружены в FSM.")

    if characters:
        # Редактируем сообщение со списком персонажей, выделяя выбранного.
        await call.message.edit_text(
            text=LobbyFormatter.format_character_list(characters),
            parse_mode='HTML',
            reply_markup=get_character_lobby_kb(characters, selected_char_id=char_id)
        )
        log.debug(f"Список персонажей для user_id={user_id} обновлен, выбран char_id={char_id}.")

        # Сохраняем ID выбранного персонажа.
        await state.update_data(char_id=char_id, user_id=user_id)

        # Вызываем обработчик меню статуса для отображения информации.
        await status_menu_start_handler(
            state=state,
            bot=bot,
            explicit_view_mode="lobby"
        )
    else:
        log.warning(f"У user_id={user_id} нет персонажей, хотя он находится в лобби выбора.")
        await ERR.generic_error(call=call)


@router.callback_query(CharacterLobby.selection, F.data == "lobby:login")
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
