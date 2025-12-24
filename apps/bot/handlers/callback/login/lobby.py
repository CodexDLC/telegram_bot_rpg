# MARKED: Uses non-InGame state: CharacterLobby
import time

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger as log
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from apps.bot.handlers.callback.onboarding.onboarding_handler import start_onboarding_process
from apps.bot.resources.fsm_states.states import CharacterLobby
from apps.bot.resources.keyboards.callback_data import LobbySelectionCallback
from apps.bot.ui_service.helpers_ui.callback_exceptions import UIErrorHandler as Err
from apps.bot.ui_service.helpers_ui.dto_helper import FSM_CONTEXT_KEY, fsm_store
from apps.bot.ui_service.helpers_ui.ui_tools import await_min_delay
from apps.common.core.container import AppContainer
from apps.common.schemas_dto import UserUpsertDTO
from apps.common.services.core_service.manager.account_manager import AccountManager

router = Router(name="login_lobby_router")


@router.callback_query(F.data == "start_adventure")
async def start_login_handler(
    call: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    session: AsyncSession,
    account_manager: AccountManager,
    container: AppContainer,
) -> None:
    """
    Обрабатывает кнопку "Начать приключение".
    Отображает лобби выбора персонажа или запускает процесс создания нового.
    """
    if not call.from_user or not call.message:
        log.warning("Handler 'start_login_handler' received update without 'from_user' or 'message'.")
        return

    user_id = call.from_user.id
    log.info(f"LoginFlow | event=start_adventure user_id={user_id}")
    await call.answer()
    start_time = time.monotonic()

    try:
        # Используем AuthClient для проверки/создания юзера
        auth_client = container.get_auth_client(session)
        user_dto = UserUpsertDTO(
            telegram_id=call.from_user.id,
            first_name=call.from_user.first_name,
            username=call.from_user.username,
            last_name=call.from_user.last_name,
            language_code=call.from_user.language_code,
            is_premium=bool(call.from_user.is_premium),
        )
        await auth_client.upsert_user(user_dto)
        log.debug(f"UserInit | status=checked user_id={user_id}")
    except SQLAlchemyError:
        log.error(f"UserInit | status=db_error user_id={user_id}", exc_info=True)
        await Err.generic_error(call=call)
        return

    # Создаем оркестратор через контейнер
    orchestrator = container.get_lobby_bot_orchestrator(session)
    state_data = await state.get_data()

    # Получаем список персонажей
    characters = await orchestrator.get_user_characters(user_id)

    characters_count = len(characters)
    log.debug(f"LoginFlow | characters_found={characters_count} user_id={user_id}")

    if characters:
        await state.set_state(CharacterLobby.selection)

        # 1. Достаем текущие данные, чтобы спасти message_menu
        current_data = await state.get_data()
        current_ctx = current_data.get(FSM_CONTEXT_KEY, {})
        saved_menu = current_ctx.get("message_menu")

        # 2. Формируем новый контекст
        new_context = {
            "user_id": user_id,
            "char_id": None,
            "message_content": None,
            "message_menu": saved_menu,
        }

        # 3. Сохраняем
        await state.update_data({FSM_CONTEXT_KEY: new_context})
        await state.update_data(characters=await fsm_store(characters))
        log.info(f"FSM | state=CharacterLobby.selection user_id={user_id}")

        lobby_view = await orchestrator.get_lobby_view(call.from_user, state_data)

        await await_min_delay(start_time, min_delay=0.5)

        if isinstance(call.message, Message) and lobby_view.content:
            await call.message.edit_text(
                text=lobby_view.content.text, parse_mode="html", reply_markup=lobby_view.content.kb
            )
        log.debug(f"UIRender | component=lobby_menu user_id={user_id}")
    else:
        log.info(f"LoginFlow | reason=no_characters_found action=start_creation user_id={user_id}")

        # Создаем "болванку" персонажа
        result_dto = await orchestrator.create_character(call.from_user)
        char_id = result_dto.new_char_id

        if not char_id:
            log.error(f"CharacterCreation | status=failed reason='Could not create character shell' user_id={user_id}")
            await Err.char_id_not_found_in_fsm(call=call)
            return

        # ИЗМЕНЕНО: Запуск нового процесса онбординга
        if isinstance(call.message, Message):
            await start_onboarding_process(
                message=call.message,
                state=state,
                char_id=char_id,
                session=session,
                container=container,  # Передаем только контейнер
            )


@router.callback_query(CharacterLobby.selection, LobbySelectionCallback.filter(F.action == "create"))
async def create_character_handler(
    call: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    session: AsyncSession,
    account_manager: AccountManager,
    container: AppContainer,
) -> None:
    """
    Обрабатывает кнопку "Создать нового персонажа" из лобби.
    """
    if not call.from_user or not call.message:
        log.warning("Handler 'create_character_handler' received update without 'from_user' or 'message'.")
        return

    user_id = call.from_user.id
    log.info(f"LoginFlow | event=create_character_from_lobby user_id={user_id}")

    orchestrator = container.get_lobby_bot_orchestrator(session)
    result_dto = await orchestrator.create_character(call.from_user)
    char_id = result_dto.new_char_id

    if not char_id:
        log.error(f"CharacterCreation | status=failed reason='Could not create character shell' user_id={user_id}")
        await Err.char_id_not_found_in_fsm(call=call)
        return

    # ИЗМЕНЕНО: Запуск нового процесса онбординга
    if isinstance(call.message, Message):
        await start_onboarding_process(
            message=call.message,
            state=state,
            char_id=char_id,
            session=session,
            container=container,  # Передаем только контейнер
        )
