# app/handlers/fsn_callback/char_creation.py
import asyncio
import logging
from aiogram import Router, F, Bot

from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.resources.fsm_states.states import CharacterCreation, StartTutorial, CharacterLobby
from app.resources.keyboards.inline_kb.loggin_und_new_character import confirm_kb, tutorial_kb, gender_kb
from app.resources.models.character_dto import CharacterCreateDTO
from app.resources.texts.buttons_callback import Buttons

from app.resources.texts.game_messages.lobby_messages import LobbyMessages
from app.resources.texts.game_messages.tutorial_messages import TutorialMessages


from app.services.helpers_module.game_validator import validate_character_name
from database.db import get_db_connection
from database.repositories import get_character_repo

log = logging.getLogger(__name__)

router = Router(name="character_creation_fsm")


@router.callback_query(CharacterCreation.choosing_gender, F.data.startswith("gender:"))
async def choose_gender_handler(call: CallbackQuery, state: FSMContext):
    """
    Обрабатывает выбор пола.
    """
    await call.answer()
    gender_value = call.data.split(":")[-1]
    gender_text_ru = Buttons.GENDER.get(f"gender:{gender_value}", "Не указан")

    await state.update_data(gender_db=gender_value, gender_display=gender_text_ru)
    await state.set_state(CharacterCreation.choosing_name)

    if isinstance(call.message, Message):
        last_message_id = await call.message.edit_text(
            LobbyMessages.NewCharacter.NAME_INPUT,
            parse_mode='HTML',
            reply_markup=None
        )
        await state.update_data(last_message_id=last_message_id.message_id)

    log.debug(f"FSM: Состояние переведено на {CharacterCreation.choosing_name.state}, Пол: {gender_value}")


@router.message(CharacterCreation.choosing_name)
async def choosing_name_handler(m: Message, state: FSMContext, bot: Bot):
    """
    Обрабатывает ввод имени.
    """
    name = m.text.strip()
    test, error_msg = validate_character_name(name)

    data = await state.get_data()
    chat_id = m.chat.id

    previous_bot_message_id = data.get("last_message_id")

    try:
        await bot.delete_message(chat_id=chat_id, message_id=m.message_id)
    except Exception as e:
        log.warning(f"Не удалось удалить сообщение игрока: {e}")

    if test:
        await state.update_data(name=name)
        await state.set_state(CharacterCreation.confirm)
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=previous_bot_message_id,
            text=LobbyMessages.NewCharacter.FINAL_CONFIRMATION.format(name=name, gender=data['gender_display']),
            parse_mode='HTML',
            reply_markup=confirm_kb()

        )
    else:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=previous_bot_message_id,
            text=f"<b>⚠️ Ошибка:</b> {error_msg}\n\n"
                 f"{LobbyMessages.NewCharacter.NAME_INPUT}",
            parse_mode='HTML',
            reply_markup=None
        )


@router.callback_query(CharacterCreation.confirm, F.data == "confirm")
async def confirm_creation_handler(call: CallbackQuery, state: FSMContext):
    """
    Обрабатывает подтверждение создания персонажа.
    """
    await call.answer()
    data = await state.get_data()

    if not data.get("name") or not data.get("gender_db"):
        await state.clear()
        return await call.message.edit_text("⚠️ Ошибка: Данные создания утеряны. Начните заново цепочку создания персонажа.")

    else:
        data_to_save = CharacterCreateDTO(
            user_id=call.from_user.id,
            name=data.get("name"),
            gender=data.get("gender_db")
        )
        log.debug(f"данный для сохранения {data_to_save}")


        async with get_db_connection() as db:
            char_repo = get_character_repo(db)
            new_char_id = await char_repo.create_character(data_to_save)
            log.info(f"Айди персонажа {new_char_id}")

        await state.clear()

        await state.update_data(character_id=new_char_id)

        await state.set_state(StartTutorial.start)

        message_to_edit = None
        for text_line, pause_duration in TutorialMessages.WAKING_UP_SEQUENCE:
            if message_to_edit is None:
                # В первую итерацию создаем сообщение
                message_to_edit = await call.message.edit_text(text_line, parse_mode='HTML')
            else:
                # В последующие - редактируем
                await call.message.edit_text(text_line, parse_mode='HTML')

            await asyncio.sleep(pause_duration)

        # А после цикла - твой код, который выводит TUTORIAL_PROMPT_TEXT
        text = Buttons.CONFIRM

        await call.message.edit_text(
            TutorialMessages.TUTORIAL_PROMPT_TEXT,
            parse_mode='HTML',
            reply_markup=tutorial_kb(text)
        )
        return None


@router.callback_query(CharacterLobby.selection, F.data == "lobby:create")
async def start_creation_handler(call: CallbackQuery, state: FSMContext):
    """
        Инициирует создание персонажа

    """
    await state.set_state(CharacterCreation.choosing_gender)
    if isinstance(call.message, Message):
        await call.message.edit_text(
            text=LobbyMessages.NewCharacter.GENDER_CHOICE, parse_mode='HTML',
            reply_markup=gender_kb())
