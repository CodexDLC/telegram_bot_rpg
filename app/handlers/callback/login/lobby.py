# app/handlers/callback/login/lobby.py
import time
from typing import Any

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger as log
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.handlers.callback.login.char_creation import start_creation_handler
from app.resources.fsm_states.states import CharacterLobby
from app.resources.keyboards.callback_data import LobbySelectionCallback
from app.services.helpers_module.callback_exceptions import UIErrorHandler as Err
from app.services.helpers_module.dto_helper import FSM_CONTEXT_KEY
from app.services.ui_service.command_service import CommandService
from app.services.ui_service.helpers_ui.ui_tools import await_min_delay
from app.services.ui_service.lobby_service import LobbyService

router = Router(name="login_lobby_router")


@router.callback_query(F.data == "start_adventure")
async def start_login_handler(call: CallbackQuery, state: FSMContext, bot: Bot, session: AsyncSession) -> None:
    """
    Обрабатывает нажатие кнопки "Начать приключение".

    Проверяет, есть ли у пользователя персонажи. Если да, отображает лобби
    выбора. Если нет, запускает процесс создания нового персонажа.

    Args:
        session:
        call (CallbackQuery): Входящий callback от кнопки.
        state (FSMContext): Состояние FSM.
        bot (Bot): Экземпляр бота.

    Returns:
        None

    """
    if not call.from_user or not call.message:
        log.warning("Хэндлер 'start_login_handler' получил обновление без 'from_user' или 'message'.")
        return

    log.info(f"Хэндлер 'start_login_handler' [start_adventure] вызван user_id={call.from_user.id}")
    await call.answer()
    start_time = time.monotonic()

    user = call.from_user

    try:
        com_service = CommandService(user)
        await com_service.create_user_in_db(session)
        log.debug(f"Failsafe: Пользователь {user.id} проверен/создан перед загрузкой персонажей.")
    except SQLAlchemyError as e:
        log.error(f"Критическая ошибка: Не удалось выполнить failsafe user creation для {user.id}: {e}", exc_info=True)
        await Err.generic_error(call=call)
        return

    # Загружаем данные о персонажах пользователя.
    log.debug(f"Загрузка персонажей для user_id={user.id}")
    lobby_service = LobbyService(user=user, state_data=await state.get_data())

    character_list = await lobby_service.get_data_characters(session)

    log.debug(f"Получены персонажи: {character_list}")

    if character_list:
        # Если у пользователя есть персонажи, показываем лобби.
        log.info(f"У user_id={user.id} есть персонажи. Переход в лобби выбора.")
        await state.set_state(CharacterLobby.selection)
        current_data = await state.get_data()
        session_context = current_data.get(FSM_CONTEXT_KEY, {})
        session_context["user_id"] = user.id
        session_context["char_id"] = None
        session_context["message_content"] = None
        await state.update_data({FSM_CONTEXT_KEY: session_context})
        log.debug(f"Состояние установлено в CharacterLobby.selection для user_id={user.id}")

        text, kb = lobby_service.get_data_lobby_start(character_list)

        await await_min_delay(start_time, min_delay=0.5)

        if isinstance(call.message, Message):
            await call.message.edit_text(text=text, parse_mode="html", reply_markup=kb)
        log.debug(f"Сообщение-лобби отправлено user_id={user.id}")
    else:
        # Если персонажей нет, запускаем процесс создания.
        log.info(f"У user_id={user.id} нет персонажей. Запуск процесса создания.")
        state_data = await state.get_data()
        session_context = state_data.get(FSM_CONTEXT_KEY, {})
        message_menu: dict[str, Any] | None = session_context.get("message_menu")
        if not message_menu:
            await Err.generic_error(call)
            return

        # Создаем "пустую" запись персонажа в БД и получаем его ID.
        char_id = await lobby_service.create_und_get_character_id(session)
        if not char_id:
            log.error(f"Не удалось создать 'оболочку' персонажа для user_id={user.id}")
            await Err.invalid_id(call=call)
            return

        # Передаем управление обработчику создания персонажа.
        await start_creation_handler(
            call=call,
            state=state,
            user_id=lobby_service.user_id,
            message_menu=message_menu,
            bot=bot,
            char_id=char_id,
        )


@router.callback_query(CharacterLobby.selection, LobbySelectionCallback.filter(F.action == "create"))
async def create_character_handler(call: CallbackQuery, state: FSMContext, bot: Bot, session: AsyncSession) -> None:
    """
    Обрабатывает нажатие "Создать нового персонажа" из лобби.

    Args:
        session
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
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    message_menu: dict[str, Any] | None = session_context.get("message_menu")
    if not message_menu:
        await Err.generic_error(call)
        return

    # Создаем "пустую" запись для нового персонажа в БД.
    lobby_service = LobbyService(user=call.from_user, state_data=state_data)
    char_id = await lobby_service.create_und_get_character_id(session)
    if not char_id:
        log.error(f"Не удалось создать 'оболочку' персонажа для user_id={user_id} из лобби.")
        await Err.invalid_id(call=call)
        return

    # Передаем управление основному обработчику создания персонажа.
    await start_creation_handler(
        call=call, state=state, bot=bot, user_id=user_id, char_id=char_id, message_menu=message_menu
    )
