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
from app.services.helpers_module.callback_exceptions import UIErrorHandler as ERR

log = logging.getLogger(__name__)

router = Router(name="login_lobby_router")


@router.callback_query(F.data == "start_adventure")
async def start_login_handler(call: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    """
    Обрабатывает нажатие кнопки "Начать приключение".

    Проверяет, есть ли у пользователя персонажи. Если да, отображает лобби
    выбора. Если нет, запускает процесс создания нового персонажа.

    Args:
        call (CallbackQuery): Входящий callback от кнопки.
        state (FSMContext): Состояние FSM.
        bot (Bot): Экземпляр бота.

    Returns:
        None
    """
    if not call.from_user:
        log.warning("Хэндлер 'start_login_handler' получил обновление без 'from_user'.")
        return

    log.info(f"Хэндлер 'start_login_handler' [start_adventure] вызван user_id={call.from_user.id}")
    await call.answer()
    start_time = time.monotonic()

    user = call.from_user

    # Загружаем данные о персонажах пользователя.
    log.debug(f"Загрузка персонажей для user_id={user.id}")
    characters_data = await load_data_auto(["characters"], user_id=user.id)
    character_list = characters_data.get("characters")
    log.debug(f"Найдено {len(character_list) if character_list else 0} персонажей.")

    lobby_service = LobbyService(characters=character_list, user=user)

    if character_list:
        # Если у пользователя есть персонажи, показываем лобби.
        log.info(f"У user_id={user.id} есть персонажи. Переход в лобби выбора.")
        await state.set_state(CharacterLobby.selection)
        # Очищаем данные предыдущего выбора, чтобы избежать некорректного состояния.
        await state.update_data(selected_char_id=None, message_content=None)
        log.debug(f"Состояние установлено в CharacterLobby.selection для user_id={user.id}")

        text, kb = await lobby_service.get_data_lobby_start()

        await await_min_delay(start_time, min_delay=0.5)

        await call.message.edit_text(text=text, parse_mode="html", reply_markup=kb)
        log.debug(f"Сообщение-лобби отправлено user_id={user.id}")
    else:
        # Если персонажей нет, запускаем процесс создания.
        log.info(f"У user_id={user.id} нет персонажей. Запуск процесса создания.")
        state_data = await state.get_data()

        # Создаем "пустую" запись персонажа в БД и получаем его ID.
        char_id = await lobby_service.create_und_get_character_id()
        if not char_id:
            log.error(f"Не удалось создать 'оболочку' персонажа для user_id={user.id}")
            await ERR.invalid_id(call=call)
            return

        # Передаем управление обработчику создания персонажа.
        await start_creation_handler(
            call=call,
            state=state,
            user_id=lobby_service.user_id,
            message_menu=state_data.get("message_menu"),
            bot=bot,
            char_id=char_id
        )


@router.callback_query(CharacterLobby.selection, F.data == "lobby:create")
async def create_character_handler(call: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    """
    Обрабатывает нажатие "Создать нового персонажа" из лобби.

    Args:
        call (CallbackQuery): Входящий callback от кнопки "Создать".
        state (FSMContext): Состояние FSM.
        bot (Bot): Экземпляр бота.

    Returns:
        None
    """
    if not call.from_user:
        log.warning("Хэндлер 'create_character_handler' получил обновление без 'from_user'.")
        return

    log.info(f"Хэндлер 'create_character_handler' [lobby:create] вызван user_id={call.from_user.id}")
    user_id = call.from_user.id
    state_data = await state.get_data()
    message_menu = state_data.get("message_menu")

    # Создаем "пустую" запись для нового персонажа в БД.
    lobby_service = LobbyService(user=call.from_user)
    char_id = await lobby_service.create_und_get_character_id()
    if not char_id:
        log.error(f"Не удалось создать 'оболочку' персонажа для user_id={user_id} из лобби.")
        await ERR.invalid_id(call=call)
        return

    # Передаем управление основному обработчику создания персонажа.
    await start_creation_handler(
        call=call,
        state=state,
        bot=bot,
        user_id=user_id,
        char_id=char_id,
        message_menu=message_menu
    )
