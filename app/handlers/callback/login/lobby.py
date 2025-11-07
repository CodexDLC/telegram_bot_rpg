# app/handlers/callback/login/lobby.py
import logging
import time
from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.handlers.callback.login.char_creation import start_creation_handler
from app.resources.fsm_states.states import CharacterLobby

from app.services.helpers_module.data_loader_service import load_data_auto

from app.services.ui_service.helpers_ui.ui_tools import await_min_delay
from app.services.ui_service.lobbyservice import LobbyService

log = logging.getLogger(__name__)

router = Router(name="login_lobby_router")


@router.callback_query(F.data == "start_adventure")
async def start_login_handler(call: CallbackQuery, state: FSMContext, bot: Bot):
    """
    Обрабатывает нажатие кнопки "Начать приключение".

    Эта функция проверяет, есть ли у пользователя уже созданные персонажи.
    Если есть, она отображает лобби выбора персонажа.
    Если нет, она автоматически запускает процесс создания нового персонажа.

    Args:
        call (CallbackQuery): Входящий callback от кнопки.
        state (FSMContext): Состояние FSM для управления данными пользователя.
        bot (Bot): Экземпляр бота.

    Returns:
        None
    """
    log.debug("Начало работы handler 'start_login_handler'")
    await call.answer()
    start_time = time.monotonic()

    if not call.from_user:
        return

    user = call.from_user

    # Загружаем данные о персонажах пользователя из базы данных.
    characters_data = await load_data_auto(["characters"], user_id=user.id)
    character_list = characters_data.get("characters")

    lobby_service = LobbyService(
        characters=character_list,
        user=user
    )

    # Если у пользователя есть хотя бы один персонаж, показываем лобби.
    if character_list:
        await state.set_state(CharacterLobby.selection)
        # Очищаем данные предыдущего выбора, чтобы избежать некорректного состояния.
        await state.update_data(selected_char_id=None, message_content=None)

        text, kb = await lobby_service.get_data_lobby_start()

        if start_time:
            await await_min_delay(start_time, min_delay=0.5)

        await call.message.edit_text(
            text=text,
            parse_mode="html",
            reply_markup=kb
        )
    # Если персонажей нет, запускаем процесс создания нового.
    else:
        log.warning("Персонажей нету, запускаем цепочку инициализации персонажа")
        state_data = await state.get_data()

        # Создаем "пустую" запись персонажа в БД и получаем его ID.
        char_id = await lobby_service.create_und_get_character_id()

        # Передаем управление обработчику создания персонажа.
        # Это позволяет избежать дублирования кода.
        await start_creation_handler(
            call=call,
            state=state,
            user_id=lobby_service.user_id,
            message_menu=state_data.get("message_menu"),
            bot=bot,
            char_id=char_id
        )


@router.callback_query(CharacterLobby.selection, F.data == "lobby:create")
async def create_character_handler(call: CallbackQuery, state: FSMContext, bot: Bot):
    """
    Обрабатывает нажатие кнопки "Создать нового персонажа" из лобби.

    Эта функция является точкой входа в процесс создания персонажа для
    пользователя, у которого уже есть другие персонажи.

    Args:
        call (CallbackQuery): Входящий callback от кнопки "Создать".
        state (FSMContext): Состояние FSM.
        bot (Bot): Экземпляр бота.

    Returns:
        None
    """
    state_data = await state.get_data()
    message_menu = state_data.get("message_menu")
    user_id = call.from_user.id

    # Создаем "пустую" запись для нового персонажа в БД.
    lobby_service = LobbyService(user=call.from_user)
    char_id = await lobby_service.create_und_get_character_id()

    # Передаем управление основному обработчику создания персонажа.
    await start_creation_handler(
        call=call,
        state=state,
        bot=bot,
        user_id=user_id,
        char_id=char_id,
        message_menu=message_menu
    )
