# app/handlers/callback/login/lobby_character_selection.py
import logging
from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.handlers.callback.ui.status_menu.character_status import status_menu_start_handler
from app.resources.fsm_states.states import CharacterLobby
from app.resources.keyboards.inline_kb.loggin_und_new_character import get_character_lobby_kb
from app.services.helpers_module.data_loader_service import load_data_auto
from app.services.helpers_module.DTO_helper import fsm_load_auto, fsm_store
from app.services.ui_service.helpers_ui.lobby_formatters import LobbyFormatter

log = logging.getLogger(__name__)

router = Router(name="lobby_fsm")


@router.callback_query(CharacterLobby.selection, F.data.startswith("lobby:select"))
async def select_character_handler(call: CallbackQuery, state: FSMContext, bot: Bot):
    """
    Обрабатывает выбор персонажа в лобби.

    Этот обработчик отвечает за:
    - Загрузку данных о персонажах из FSM или базы данных.
    - Обновление списка персонажей с выделением выбранного.
    - Отображение или обновление подробной информации (статус) о выбранном персонаже.
    - Сохранение актуального состояния в FSM.

    Args:
        call (CallbackQuery): Входящий callback от выбора персонажа.
        state (FSMContext): Состояние FSM.
        bot (Bot): Экземпляр бота.

    Returns:
        None
    """
    await call.answer()
    char_id = int(call.data.split(":")[-1])

    # --- 1. ЗАГРУЗКА ДАННЫХ О ПЕРСОНАЖАХ ---
    # Пытаемся получить список персонажей из хранилища FSM, чтобы избежать лишних запросов к БД.
    characters = await fsm_load_auto(state=state, key="characters") or None

    # --- 2. ПЕРВИЧНАЯ ЗАГРУЗКА ИЗ БД ---
    # Если в FSM данных нет (например, первый вход в лобби), загружаем их из базы данных.
    if characters is None:
        log.info("Данных 'characters' нет в FSM, загружаю из БД...")
        get_data = await load_data_auto(
            ["characters", "character_stats"],
            character_id=char_id,
            user_id=call.from_user.id,
        )
        # Сохраняем полученные данные в FSM для последующих обращений.
        await state.update_data(
            characters=await fsm_store(value=get_data.get("characters")),
            character_stats=await fsm_store(value=get_data.get("character_stats"))
        )

    # --- 3. ПОЛУЧЕНИЕ АКТУАЛЬНЫХ ДАННЫХ FSM ---
    # Загружаем все данные из FSM, чтобы иметь самую свежую информацию.
    state_data = await state.get_data()
    characters = await fsm_load_auto(state=state, key="characters") or state_data.get("characters")

    # --- 4. ОБНОВЛЕНИЕ ИНТЕРФЕЙСА ---
    if characters:
        # Редактируем сообщение со списком персонажей, визуально выделяя выбранного.
        await call.message.edit_text(
            text=LobbyFormatter.format_character_list(characters),
            parse_mode='HTML',
            reply_markup=get_character_lobby_kb(characters, selected_char_id=char_id)
        )

        # Сохраняем ID выбранного персонажа и пользователя для последующего использования.
        await state.update_data(char_id=char_id, user_id=call.from_user.id)

        # Вызываем обработчик меню статуса, чтобы отобразить или обновить
        # подробную информацию о персонаже в отдельном сообщении.
        await status_menu_start_handler(
            state=state,
            bot=bot,
            explicit_view_mode="lobby"  # Указываем, что мы находимся в лобби.
        )

    else:
        # Обработка маловероятного случая, когда у пользователя нет персонажей,
        # хотя он находится в этом обработчике.
        log.warning(f"У пользователя {call.from_user.id} нет персонажей.")
        await call.message.edit_text("У вас нет созданных персонажей.")


@router.callback_query(CharacterLobby.selection, F.data == "lobby:login")
async def start_logging_handler(call: CallbackQuery, state: FSMContext, bot: Bot):
    """
    Обрабатывает нажатие кнопки "Войти в игру".

    На данный момент является заглушкой. В будущем здесь будет реализована
    логика входа персонажа в игровой мир, включая проверку туториалов и
    загрузку соответствующего игрового состояния.

    Args:
        call (CallbackQuery): Входящий callback от кнопки "Войти в игру".
        state (FSMContext): Состояние FSM.
        bot (Bot): Экземпляр бота.

    Returns:
        None
    """
    log.debug(f"Начало работы start_logging_handler ")
    await call.answer()
    state_data = await state.get_data()
    message_content = state_data.get("message_content")
    message_menu = state_data.get("message_menu")
    char_id = state_data.get("activ_char_id")

    # TODO: Реализовать полную логику входа в игру.
    # TODO: Реализовать систему сохранения прогресса туториала,
    # чтобы возвращать игрока на нужный этап после пересоздания или логина.

    # --- ЗАГЛУШКА: ИНФОРМИРОВАНИЕ О НЕРАБОТАЮЩЕЙ ФУНКЦИИ ---
    # Редактируем оба сообщения (меню и контент), чтобы показать, что функция в разработке.
    await bot.edit_message_text(
        chat_id=message_menu.get("chat_id"),
        message_id=message_menu.get("message_id"),
        text="Логина в игру пока нету",
        parse_mode='HTML',
        reply_markup=None
    )

    await bot.edit_message_text(
        chat_id=message_content.get("chat_id"),
        message_id=message_content.get("message_id"),
        text=" Логина в игру пока нету",
        parse_mode='HTML',
        reply_markup=None
    )

    log.debug(f"Состояние FSM при попытке логина: {state_data}")
