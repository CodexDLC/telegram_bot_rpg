# app/handlers/callback/login/lobby_character_selection.py
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
        Обрабатывает callback старта путешествия
        если есть персонажи возвращает список персонажей и клавиатуру выбора и логина.
        А если его нет запускает цепочку инициализации персонажа.

    """
    log.debug("Начало работы handler 'start_login_handler'")
    await call.answer()
    start_time = time.monotonic()

    if not call.from_user:
        return

    user = call.from_user


    if user is not None:
        # 1. Загружаем словарь (как и раньше)
        characters_data = await load_data_auto(["characters"], user_id=user.id)
    else:
        characters_data = {}

    character_list = characters_data.get("characters")
    lobby_service = LobbyService(
        characters=character_list,
        user=user
    )

    if character_list:

        await state.set_state(CharacterLobby.selection)
        await state.update_data(selected_char_id=None, message_content=None)

        text, kb = await lobby_service.get_data_lobby_start()

        if start_time:
            await await_min_delay(start_time, min_delay=0.5)

        await call.message.edit_text(
            text=text,
            parse_mode="html",
            reply_markup=kb
        )

    else:
        log.warning("Персонажей нету запускаем цепочку инициализации персонажа")
        state_data = await state.get_data()

        char_id = await lobby_service.create_und_get_character_id()

        await start_creation_handler(
            call=call,
            state=state,
            user_id=lobby_service.user_id,
            message_menu= state_data.get("message_menu"),
            bot=bot,
            char_id=char_id
        )


@router.callback_query(CharacterLobby.selection, F.data == "lobby:create")
async def create_character_handler(call: CallbackQuery, state: FSMContext, bot: Bot):
    # 1. Получаем нужные данные из FSM
    state_data = await state.get_data()
    message_menu = state_data.get("message_menu")
    user_id = call.from_user.id

    # 2. Создаем "оболочку" персонажа
    # (Точно так же, как ты делал в start_login_handler)
    lobby_service = LobbyService(user=call.from_user)
    char_id = await lobby_service.create_und_get_character_id()

    # 3. Вызываем хэндлер создания
    # (Твоя главная идея - "просто должен вызывать")
    await start_creation_handler(
        call=call,
        state=state,
        bot=bot,
        user_id=user_id,
        char_id=char_id,
        message_menu=message_menu
    )
