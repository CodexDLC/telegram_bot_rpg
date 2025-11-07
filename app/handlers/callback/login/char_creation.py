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
        char_id: int,
        message_menu: dict[str, int]):
    """
    Инициирует процесс создания нового персонажа.

    Эта функция запускается, когда пользователь нажимает кнопку создания
    персонажа. Она подготавливает интерфейс, обновляет меню и контентное
    сообщение, а также переводит FSM в состояние выбора пола.

    Args:
        call (CallbackQuery): Входящий callback от пользователя.
        state (FSMContext): Состояние FSM для управления данными пользователя.
        bot (Bot): Экземпляр бота для взаимодействия с API Telegram.
        user_id (int): ID пользователя Telegram.
        char_id (int): ID создаваемого персонажа в базе данных.
        message_menu (dict[str, int]): Словарь с ID чата и сообщения для меню.

    Returns:
        None
    """
    await call.answer()
    start_time = time.monotonic()

    # Инициализируем сервис меню для стадии "creation".
    # Это позволяет получить нужный текст и клавиатуру для текущего этапа.
    ms = MenuService(
        game_stage="creation",
        char_id=char_id,
    )
    text, kb = ms.get_data_menu()

    # Обеспечиваем минимальную задержку для плавности UI.
    if start_time:
        await await_min_delay(start_time, min_delay=0.3)

    # Обновляем верхнее сообщение (меню).
    await bot.edit_message_text(
        chat_id=message_menu.get("chat_id"),
        message_id=message_menu.get("message_id"),
        text=text,
        parse_mode="html",
        reply_markup=kb
    )

    # Создаем или обновляем нижнее сообщение (контент).
    await create_message_content_start_creation(user_id=user_id, call=call, state=state, bot=bot)
    # Устанавливаем следующее состояние FSM - выбор пола.
    await state.set_state(CharacterCreation.choosing_gender)
    await state.update_data(user_id=user_id, char_id=char_id)
    log.debug(f"Состояние state в конце start_creation_handler {await state.get_data()}")


async def create_message_content_start_creation(
        call: CallbackQuery,
        state: FSMContext,
        user_id: int,
        bot: Bot
):
    """
    Создает или редактирует контентное сообщение для этапа создания персонажа.

    Эта функция проверяет, существует ли уже сообщение для контента. Если нет,
    создает новое. Если да, редактирует его, чтобы отобразить актуальную
    информацию для начала создания персонажа (выбор пола).

    Args:
        call (CallbackQuery): Входящий callback от пользователя.
        state (FSMContext): Состояние FSM для доступа к данным.
        user_id (int): ID пользователя Telegram.
        bot (Bot): Экземпляр бота.

    Returns:
        None
    """
    start_time = time.monotonic()

    # Сервис OnboardingService предоставляет тексты и клавиатуры для этапов создания персонажа.
    create_service = OnboardingService(user_id=user_id)
    text, kb = create_service.get_data_start_creation_content()

    state_data = await state.get_data()
    message_content = state_data.get("message_content") or None

    # Если контентное сообщение еще не было создано, создаем его.
    # Это происходит при первом запуске процесса создания персонажа.
    if message_content is None:
        log.debug(f"message_content = {message_content} запускаем создание нового сообщения ")

        if start_time:
            await await_min_delay(start_time, min_delay=0.3)

        msg = await call.message.answer(
            text=text,
            parse_mode="html",
            reply_markup=kb
        )

        # Сохраняем информацию о новом сообщении в FSM для последующих правок.
        message_content = {
            "chat_id": msg.chat.id,
            "message_id": msg.message_id
        }
        await state.update_data(message_content=message_content)

    # Если сообщение уже существует, просто редактируем его.
    # Это предотвращает "засорение" чата новыми сообщениями.
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
    Обрабатывает выбор пола персонажа.

    Функция получает callback с выбором пола, обновляет контентное сообщение,
    сохраняет выбор в FSM и переводит машину состояний на следующий шаг —
    ввод имени.

    Args:
        call (CallbackQuery): Входящий callback с данными о поле (e.g., "gender:male").
        state (FSMContext): Состояние FSM.
        bot (Bot): Экземпляр бота.

    Returns:
        None
    """
    log.debug(f"Старт работы choose_gender_handler")
    await call.answer()
    start_time = time.monotonic()
    gender_callback = call.data
    state_data = await state.get_data()

    # Проверка на случай, если пользователь "потерялся" в диалоге и FSM пуст.
    if not state_data:
        log.error(f"Стейт дата пуст {state_data}")
        await error_msg_default(call=call)
        return

    user_id = state_data.get("user_id")

    create_service = OnboardingService(user_id=user_id)
    # Получаем текст для сообщения и два представления пола: для UI и для БД.
    text, gender_display, gender_db = create_service.get_data_start_gender(
        gender_callback=gender_callback)

    message_content = state_data.get("message_content") or None

    if message_content is None:
        log.error(f"message_content = {message_content} ошибка запуска")
        await error_msg_default(call=call)
        return

    if start_time:
        await await_min_delay(start_time, min_delay=0.3)

    # Обновляем контентное сообщение, предлагая ввести имя.
    await bot.edit_message_text(
        chat_id=message_content.get("chat_id"),
        message_id=message_content.get("message_id"),
        text=text,
        parse_mode="html",
        reply_markup=None  # Убираем клавиатуру выбора пола.
    )
    await state.update_data(gender_db=gender_db, gender_display=gender_display)
    await state.set_state(CharacterCreation.choosing_name)

    log.debug(f"FSM: Состояние переведено на {CharacterCreation.choosing_name.state}, Пол: {gender_db}")
    log.debug(f"Состояние state в конце gender {await state.get_data()}")


@router.message(CharacterCreation.choosing_name)
async def choosing_name_handler(m: Message, state: FSMContext, bot: Bot):
    """
    Обрабатывает ввод имени персонажа.

    Функция получает сообщение от пользователя, валидирует его как имя
    персонажа. В случае успеха, переводит FSM в состояние подтверждения.
    В случае ошибки — информирует пользователя.

    Args:
        m (Message): Входящее сообщение с именем.
        state (FSMContext): Состояние FSM.
        bot (Bot): Экземпляр бота.

    Returns:
        None
    """
    log.debug(f"Старт работы choosing_name_handler имя {m.text.strip()}")
    name = m.text.strip()
    is_valid, error_msg = validate_character_name(name)

    state_data = await state.get_data()
    message_content = state_data.get("message_content")
    chat_id = message_content.get("chat_id")

    # Удаляем сообщение пользователя с именем, чтобы не засорять чат.
    try:
        await bot.delete_message(chat_id=chat_id, message_id=m.message_id)
    except Exception as e:
        log.warning(f"Не удалось удалить сообщение игрока: {e}")

    # Если имя прошло валидацию.
    if is_valid:
        await state.update_data(name=name)
        await state.set_state(CharacterCreation.confirm)
        # Показываем финальное окно подтверждения.
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_content.get("message_id"),
            text=LobbyMessages.NewCharacter.FINAL_CONFIRMATION.format(name=name, gender=state_data['gender_display']),
            parse_mode='HTML',
            reply_markup=confirm_kb()
        )
    # Если имя невалидно.
    else:
        # Показываем ошибку и просим ввести имя еще раз.
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_content.get("message_id"),
            text=f"<b>⚠️ Ошибка:</b> {error_msg}\n\n"
                 f"{LobbyMessages.NewCharacter.NAME_INPUT}",
            parse_mode='HTML',
            reply_markup=None
        )

    log.debug(f"Состояние state в конце name {await state.get_data()}")


@router.callback_query(CharacterCreation.confirm, F.data == "confirm")
async def confirm_creation_handler(call: CallbackQuery, state: FSMContext, bot: Bot):
    """
    Обрабатывает финальное подтверждение создания персонажа.

    Эта функция сохраняет данные персонажа (имя, пол) в базу данных,
    очищает FSM от временных данных создания и инициирует начало
    туториала, показывая анимацию "пробуждения".

    Args:
        call (CallbackQuery): Входящий callback от кнопки подтверждения.
        state (FSMContext): Состояние FSM.
        bot (Bot): Экземпляр бота.

    Returns:
        None
    """
    await call.answer()

    state_data = await state.get_data()
    user = call.from_user

    # Проверяем, что все необходимые данные для создания есть в FSM.
    if not state_data.get("name") or not state_data.get("gender_db"):
        await state.clear()
        await error_msg_default(call=call)
        return

    # Переводим FSM в состояние туториала.
    await state.set_state(StartTutorial.start)

    # Готовим DTO для обновления записи о персонаже в БД.
    char_update_dto = CharacterOnboardingUpdateDTO(
        name=state_data.get("name"),
        gender=state_data.get("gender_db"),
        game_stage="tutorial_stats"  # Устанавливаем следующий этап игры.
    )

    create_service = OnboardingService(user_id=user.id, char_id=state_data.get("char_id"))
    await create_service.update_character_db(char_update_dto=char_update_dto)

    # Очищаем FSM, оставляя только ключевые данные, необходимые для игры.
    # Это важно, чтобы не хранить лишнюю информацию после создания персонажа.
    await state.set_data({
        "message_menu": state_data.get("message_menu"),
        "message_content": state_data.get("message_content"),
        "char_id": state_data.get("char_id")
    })

    state_data = await state.get_data()
    message_content = state_data.get("message_content")

    # Запускаем красивую анимацию "пробуждения" персонажа.
    await animate_message_sequence(
        message_to_edit=message_content,
        sequence=TutorialMessages.WAKING_UP_SEQUENCE,
        bot=bot,
        final_reply_markup=None
    )

    # После анимации показываем стартовый экран туториала.
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

    log.debug(f"Состояние state в конце confirm {await state.get_data()}")
