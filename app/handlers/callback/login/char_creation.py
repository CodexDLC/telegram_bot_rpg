# app/handlers/fsn_callback/char_creation.py

import logging
import time
from aiogram import Router, F, Bot

from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.resources.fsm_states.states import CharacterCreation, StartTutorial
from app.resources.keyboards.inline_kb.loggin_und_new_character import confirm_kb
from app.resources.schemas_dto.character_dto import CharacterOnboardingUpdateDTO


from app.resources.texts.game_messages.lobby_messages import LobbyMessages
from app.resources.texts.game_messages.tutorial_messages import TutorialMessages

from app.services.ui_service.menu_service import MenuService
from app.services.ui_service.new_character.onboarding_service import OnboardingService

from app.services.helpers_module.game_validator import validate_character_name
from app.services.helpers_module.helper_id_callback import error_msg_default
from app.services.ui_service.helpers_ui.ui_tools import await_min_delay, animate_message_sequence

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
        game_stage="creation",
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
async def choose_gender_handler(call: CallbackQuery, state: FSMContext, bot: Bot):
    """
    Обрабатывает выбор пола.
    """

    await call.answer()
    start_time = time.monotonic()
    gender_callback = call.data
    state_data = await state.get_data()
    if not state_data:
        log.error(f"Стейт дата пуст {state_data}")
        await error_msg_default(call=call)

    user_id = state_data.get("user_id")

    create_service = OnboardingService(user_id=user_id)
    text, gender_display, gender_db = create_service.get_data_start_gender(
        gender_callback=gender_callback)

    message_content = state_data.get("message_content") or None

    if message_content is None:
        log.error(f"message_content = {message_content} ошибка запуска")
        await error_msg_default(call=call)

    if start_time:
        await await_min_delay(start_time, min_delay=0.3)

    await bot.edit_message_text(
        chat_id=message_content.get("chat_id"),
        message_id=message_content.get("message_id"),
        text=text,
        parse_mode="html",
        reply_markup=None
    )
    await state.update_data(gender_db=gender_db, gender_display=gender_display)
    await state.set_state(CharacterCreation.choosing_name)

    log.debug(f"FSM: Состояние переведено на {CharacterCreation.choosing_name.state}, Пол: {gender_db}")


@router.message(CharacterCreation.choosing_name)
async def choosing_name_handler(m: Message, state: FSMContext, bot: Bot):
    """
    Обрабатывает ввод имени.
    """
    name = m.text.strip()
    test, error_msg = validate_character_name(name)

    state_data = await state.get_data()
    message_content = state_data.get("message_content")
    chat_id = message_content.get("chat_id")

    try:
        await bot.delete_message(chat_id=chat_id, message_id=m.message_id)
    except Exception as e:
        log.warning(f"Не удалось удалить сообщение игрока: {e}")

    if test:
        await state.update_data(name=name)
        await state.set_state(CharacterCreation.confirm)
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_content.get("message_id"),
            text=LobbyMessages.NewCharacter.FINAL_CONFIRMATION.format(name=name, gender=state_data['gender_display']),
            parse_mode='HTML',
            reply_markup=confirm_kb()

        )

    else:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_content.get("message_id"),
            text=f"<b>⚠️ Ошибка:</b> {error_msg}\n\n"
                 f"{LobbyMessages.NewCharacter.NAME_INPUT}",
            parse_mode='HTML',
            reply_markup=None
        )


@router.callback_query(CharacterCreation.confirm, F.data == "confirm")
async def confirm_creation_handler(call: CallbackQuery, state: FSMContext, bot: Bot):
    """
    Обрабатывает подтверждение создания персонажа.
    """
    await call.answer()

    state_data = await state.get_data()
    user = call.from_user

    if not state_data.get("name") or not state_data.get("gender_db"):
        await state.clear()
        await error_msg_default(call=call)

    await state.set_state(StartTutorial.start)

    char_update_dto = CharacterOnboardingUpdateDTO(
        name=state_data.get("name"),
        gender=state_data.get("gender_db"),
        game_stage="tutorial_stats"
    )

    create_service = OnboardingService(user_id=user.id, char_id=state_data.get("char_id"))
    await create_service.update_character_db(char_update_dto=char_update_dto)

    state_data = await state.get_data()
    message_content = state_data.get("message_content")

    # Вызываем хелпер анимации
    await animate_message_sequence(
        message_to_edit=message_content,
        sequence=TutorialMessages.WAKING_UP_SEQUENCE,
        bot=bot,
        final_reply_markup=None
    )

    # 5. ФИНАЛЬНЫЙ ЭКРАН
    # (После завершения анимации, хелпер уже ушел)
    text, kb = create_service.get_data_start(
        name=state_data.get("name"),
        gender=state_data.get("gender_display")
    )

    await bot.edit_message_text(
        chat_id=message_content.get("chat_id"),
        message_id=message_content.get("message_id"),
        text=text,
        parse_mode='HTML',
        reply_markup=kb
    )

