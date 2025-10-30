# app/handlers/callback/login/lobby_character_selection.py
import logging
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message


from app.resources.fsm_states.states import CharacterCreation, CharacterLobby
from app.resources.keyboards.inline_kb.loggin_und_new_character import gender_kb, get_character_lobby_kb
from app.resources.texts.game_messages.lobby_messages import LobbyMessages
from app.services.data_loader_service import load_data_auto
from app.services.helpers_module.ui.lobby_formatters import LobbyFormatter


log = logging.getLogger(__name__)

router = Router(name="login_lobby_router")




@router.callback_query(F.data == "start_adventure")
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
    characters = None

    if user is not None:
        characters = await load_data_auto(["characters"], user_id=user.id)


    if characters:
        await state.set_state(CharacterLobby.selection)
        await state.update_data(selected_char_id=None, message_content=None)

        await call.message.edit_text(
            text=LobbyFormatter.format_character_list(characters.get("characters")),
            parse_mode='HTML',
            reply_markup=get_character_lobby_kb(characters.get("characters"), selected_char_id=None)
        )
        log.debug(f"Персонажи найдены: {characters} выводим меню выбора персонажа")

    else:
        log.warning("Персонажей нету запускаем цепочку инициализации персонажа")
        await state.set_state(CharacterCreation.choosing_gender)
        if isinstance(call.message, Message):
            await call.message.edit_text(
                text=LobbyMessages.NewCharacter.GENDER_CHOICE,
                parse_mode='HTML',
                reply_markup=gender_kb())