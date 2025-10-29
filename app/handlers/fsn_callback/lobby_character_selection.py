# app/handlers/fsn_callback/lobby_character_selection.py
import logging
from aiogram import Router, F

from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.resources.fsm_states.states import CharacterLobby
from app.resources.keyboards.inline_kb.loggin_und_new_character import get_character_lobby_kb
from app.resources.texts.buttons_callback import LOBBY_SELECT, LOBBY_ACTION_LOGIN
from app.resources.texts.game_messages.lobby_messages import LobbyMessages
from app.services.helpers_module.DTO_helper import fsm_load_auto, fsm_store
from database.db import get_db_connection
from database.repositories import get_character_repo

log = logging.getLogger(__name__)

router = Router(name="lobby_fsm")


@router.callback_query(CharacterLobby.selection,F.data.startswith(LOBBY_SELECT))
async def select_character_handler(call: CallbackQuery, state: FSMContext):
    """
    Обрабатывает выбор персонажа.
    """
    await call.answer()
    user = call.from_user
    char_id = int(call.data.split(":")[-1])

    characters = await fsm_load_auto(state=state, key="characters") or None


    if characters is None:
        async with get_db_connection() as db:
            char_repo = get_character_repo(db)
            characters = await char_repo.get_characters(user.id)
            log.debug(f"🔃 Персонажи найдены в дата базе: {characters}")

    if characters:
        kb = get_character_lobby_kb(characters, selected_char_id=char_id)
        text = LobbyMessages.CharacterSelection.HEADER_TEXT
        await call.message.edit_text(text, reply_markup=kb)
        chars = await fsm_store(value=characters)
        log.debug(f"Состояние characters перед сохранения в FSM: {chars}")

        await state.update_data(
            selected_char_id=char_id,
            characters=chars)

@router.callback_query(CharacterLobby.start_logging, F.data==LOBBY_ACTION_LOGIN)
async def start_logging_handler(call: CallbackQuery, state: FSMContext):
    pass