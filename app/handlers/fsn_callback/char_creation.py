# app/handlers/fsn_callback/char_creation.py
import asyncio
import logging
import time
from aiogram import Router, F, Bot

from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.resources.fsm_states.states import CharacterCreation, StartTutorial
from app.resources.keyboards.inline_kb.loggin_und_new_character import confirm_kb, tutorial_kb
from app.resources.texts.buttons_callback import Buttons, GameStage

from app.resources.texts.game_messages.lobby_messages import LobbyMessages
from app.resources.texts.game_messages.tutorial_messages import TutorialMessages
from app.services.game_service.menu_service import MenuService
from app.services.game_service.new_character.onboarding_service import OnboardingService

from app.services.helpers_module.game_validator import validate_character_name
from app.services.helpers_module.helper_id_callback import get_int_id_type
from app.services.ui_service.helpers_ui.ui_tools import await_min_delay
from database.repositories import get_character_repo
from database.session import get_async_session

log = logging.getLogger(__name__)

router = Router(name="character_creation_fsm")



async def start_creation_handler(
        call: CallbackQuery,
        state: FSMContext,
        bot: Bot,
        user_id: int,
        char_id : int,
        message_menu: dict[str, int]):
    """
        Инициирует создание персонажа

    """
    await call.answer()
    start_time = time.monotonic()


    ms = MenuService(
        game_stage="",
        char_id=char_id,
    )

    text, kb = ms.get_data_menu()

    if start_time:
        await await_min_delay(start_time, min_delay=0.3)

    await bot.edit_message_text(
        chat_id=message_menu.get("chat_id"),
        message_id=message_menu.get("message_id"),
        text=text,
        parse_mode="html",
        reply_markup=kb
    )

    await create_message_content_start_creation(user_id=user_id, call=call, state=state, bot=bot)
    await state.set_state(CharacterCreation.choosing_gender)

async def create_message_content_start_creation(
        call: CallbackQuery,
        state: FSMContext,
        user_id: int,
        bot: Bot
        ):
    """
    Инициализация второго сообщения при создании персонажа
    """

    start_time = time.monotonic()
    create_service = OnboardingService(user_id=user_id)
    text, kb = create_service.get_data_start_creation_content()

    state_data = await state.get_data()
    message_content = state_data.get("message_content") or None

    if message_content is None:
        log.debug(f"message_content = {message_content} запускаем создание нового сообщения ")

        if start_time:
            await await_min_delay(start_time, min_delay=0.3)

        msg = await call.message.answer(
                text=text,
                parse_mode="html",
                reply_markup=kb
            )

        message_content = {
            "chat_id": msg.chat.id,
            "message_id": msg.message_id
        }
        await state.update_data(message_content=message_content)

    else:
        log.debug(f"message_content = {message_content} запускаем редактирование старого сообщения")

        if start_time:
            await await_min_delay(start_time, min_delay=0.3)

        await bot.edit_message_text(
            chat_id=message_content.get("chat_id"),
            message_id=message_content.get("message_id"),
            text=text,
            parse_mode="html",
            reply_markup=kb
            )


@router.callback_query(CharacterCreation.choosing_gender, F.data.startswith("gender:"))
async def choose_gender_handler(call: CallbackQuery, state: FSMContext):
    """
    Обрабатывает выбор пола.
    """

    await call.answer()
    gender_value = get_int_id_type(call=call)
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
    message_menu = data.get("message_menu")

    if not data.get("name") or not data.get("gender_db"):
        await state.clear()
        return await call.message.edit_text("⚠️ Ошибка: Данные создания утеряны. Начните заново цепочку создания персонажа.")

    else:
        data_to_save = CharacterCreateDTO(
            user_id=call.from_user.id,
            name=data.get("name"),
            gender=data.get("gender_db"),
            game_stage=GameStage.TUTORIAL_STATS

        )
        log.debug(f"данный для сохранения {data_to_save}")

        try:
            async with get_async_session() as session:
                char_repo = get_character_repo(session)
                new_char_id = await char_repo.create_character(data_to_save)
                log.info(f"Айди персонажа {new_char_id}")
        except Exception as e:
            log.warning(f"Ошибка создания персонажа: {e}")

    await state.clear()

    await state.update_data(
            character_id=new_char_id,
            message_menu=message_menu
        )

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
    text = Buttons.TUTORIAL_START_BUTTON

    await call.message.edit_text(
            TutorialMessages.TUTORIAL_PROMPT_TEXT,
            parse_mode='HTML',
            reply_markup=tutorial_kb(text)
        )
    return None


