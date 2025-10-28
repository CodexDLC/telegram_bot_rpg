# app/handlers/callback/login/lobby.py
import logging
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.resources.fsm_states.states import CharacterCreation, StartTutorial
from app.resources.keyboards.inline_kb.loggin_und_new_character import gender_kb, tutorial_kb
from app.resources.texts.buttons_callback import START_ADVENTURE_CALLBACK
from app.resources.texts.game_messages.lobby_messages import LobbyMessages
from app.resources.texts.game_messages.tutorial_messages import TutorialMessages

from database.db import get_db_connection
from database.repositories import get_character_repo

log = logging.getLogger(__name__)

router = Router(name="login_lobby_router")




@router.callback_query(F.data == START_ADVENTURE_CALLBACK)
async def start_login_handler(call: CallbackQuery, state: FSMContext):
    """
        Обрабатывает callback старта путешествия
        если есть персонажи возвращает список персонажей и клавиатуру выбора и логина.
        А если его нет запускает цепочку инициализации персонажа.

    """
    await call.answer()

    log.debug("Callback старт путешествия пойман")
    if not call.from_user:
        return
    user = call.from_user

    async with get_db_connection() as db:
        char_repo = get_character_repo(db)
        characters = await char_repo.get_characters(user.id)

    if characters:
        # TODO: организовать выбор персонажа через функцию которая вернет текст для сообщения и данные для КБ
        # заглушка что бы не пересоздавать персонажа потом заменить на другой стартовый текст
        # брать например и дискрипшена локации где находиться или придумать что то другое
        log.debug(f"Персонажи найдены: {characters} выводим меню выбора персонажа")
    else:
        log.warning("Персонажей нету запускаем цепочку инициализации персонажа")
        await state.set_state(CharacterCreation.choosing_gender)
        if isinstance(call.message, Message):
            await call.message.edit_text(text=LobbyMessages.NewCharacter.GENDER_CHOICE, parse_mode='HTML', reply_markup=gender_kb())