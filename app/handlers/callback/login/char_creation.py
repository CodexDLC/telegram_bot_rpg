# app/handlers/callback/login/char_creation.py
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
from app.services.helpers_module.callback_exceptions import error_msg_default
from app.services.ui_service.helpers_ui.ui_tools import await_min_delay, animate_message_sequence

log = logging.getLogger(__name__)

router = Router(name="character_creation_fsm")


async def start_creation_handler(
        call: CallbackQuery,
        state: FSMContext,
        bot: Bot,
        user_id: int,
        char_id: int,
        message_menu: dict[str, int]
) -> None:
    """
    Инициирует процесс создания нового персонажа.

    Запускается после создания "оболочки" персонажа. Подготавливает
    интерфейс, обновляет меню, создает контентное сообщение и переводит
    FSM в состояние выбора пола.

    Args:
        call (CallbackQuery): Входящий callback.
        state (FSMContext): Состояние FSM.
        bot (Bot): Экземпляр бота.
        user_id (int): ID пользователя Telegram.
        char_id (int): ID создаваемого персонажа в базе данных.
        message_menu (dict[str, int]): ID чата и сообщения для меню.

    Returns:
        None
    """
    log.info(f"Хэндлер 'start_creation_handler' вызван user_id={user_id}, char_id={char_id}")
    await call.answer()
    start_time = time.monotonic()

    # Инициализируем сервис меню для получения нужного текста и клавиатуры.
    ms = MenuService(game_stage="creation", char_id=char_id)
    text, kb = ms.get_data_menu()
    log.debug("Данные для меню получены от MenuService.")

    await await_min_delay(start_time, min_delay=0.3)

    # Обновляем верхнее сообщение (меню).
    if not message_menu or not message_menu.get("chat_id") or not message_menu.get("message_id"):
        log.error(f"Некорректные данные 'message_menu' для user_id={user_id}: {message_menu}")
        await error_msg_default(call=call)
        return
    await bot.edit_message_text(
        chat_id=message_menu.get("chat_id"),
        message_id=message_menu.get("message_id"),
        text=text,
        parse_mode="html",
        reply_markup=kb
    )
    log.debug(f"Сообщение-меню {message_menu.get('message_id')} обновлено для user_id={user_id}.")

    # Создаем или обновляем нижнее сообщение (контент).
    await create_message_content_start_creation(user_id=user_id, call=call, state=state, bot=bot)

    # Устанавливаем следующее состояние FSM.
    await state.set_state(CharacterCreation.choosing_gender)
    await state.update_data(user_id=user_id, char_id=char_id)
    log.info(f"FSM для user_id={user_id} переведен в состояние 'CharacterCreation.choosing_gender'.")
    log.debug(f"Данные FSM в конце 'start_creation_handler': {await state.get_data()}")


async def create_message_content_start_creation(
        call: CallbackQuery,
        state: FSMContext,
        user_id: int,
        bot: Bot
) -> None:
    """
    Создает или редактирует контентное сообщение для этапа создания персонажа.

    Args:
        call (CallbackQuery): Входящий callback.
        state (FSMContext): Состояние FSM.
        user_id (int): ID пользователя.
        bot (Bot): Экземпляр бота.

    Returns:
        None
    """
    log.debug(f"Запуск 'create_message_content_start_creation' для user_id={user_id}")
    start_time = time.monotonic()

    create_service = OnboardingService(user_id=user_id)
    text, kb = create_service.get_data_start_creation_content()
    log.debug("Данные для контентного сообщения получены от OnboardingService.")

    state_data = await state.get_data()
    message_content = state_data.get("message_content")

    await await_min_delay(start_time, min_delay=0.3)

    if message_content is None:
        log.debug(f"Контентное сообщение для user_id={user_id} не найдено, создается новое.")
        msg = await call.message.answer(text=text, parse_mode="html", reply_markup=kb)
        message_content = {"chat_id": msg.chat.id, "message_id": msg.message_id}
        await state.update_data(message_content=message_content)
        log.info(f"Создано новое контентное сообщение {msg.message_id} для user_id={user_id}.")
    else:
        log.debug(f"Контентное сообщение {message_content.get('message_id')} для user_id={user_id} будет отредактировано.")
        try:
            await bot.edit_message_text(
                chat_id=message_content.get("chat_id"),
                message_id=message_content.get("message_id"),
                text=text,
                parse_mode="html",
                reply_markup=kb
            )
            log.debug("Контентное сообщение успешно отредактировано.")
        except Exception as e:
            log.exception(f"Не удалось отредактировать контентное сообщение для user_id={user_id}: {e}")
            await error_msg_default(call=call)


@router.callback_query(CharacterCreation.choosing_gender, F.data.startswith("gender:"))
async def choose_gender_handler(call: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    """
    Обрабатывает выбор пола персонажа.

    Сохраняет выбор в FSM и переводит на следующий шаг — ввод имени.

    Args:
        call (CallbackQuery): Callback с данными о поле (e.g., "gender:male").
        state (FSMContext): Состояние FSM.
        bot (Bot): Экземпляр бота.

    Returns:
        None
    """
    if not call.from_user:
        log.warning("Хэндлер 'choose_gender_handler' получил обновление без 'from_user'.")
        return

    gender_callback = call.data
    log.info(f"Хэндлер 'choose_gender_handler' [{gender_callback}] вызван user_id={call.from_user.id}")
    await call.answer()
    start_time = time.monotonic()

    state_data = await state.get_data()
    user_id = state_data.get("user_id")
    char_id = state_data.get("char_id")
    message_content = state_data.get("message_content")

    if not all([user_id, char_id, message_content]):
        log.warning(f"Недостаточно данных в FSM для user_id={call.from_user.id} в 'choose_gender_handler'. Данные: {state_data}")
        await error_msg_default(call=call)
        return

    create_service = OnboardingService(user_id=user_id, char_id=char_id)
    text, gender_display, gender_db = create_service.get_data_start_gender(gender_callback=gender_callback)
    log.debug(f"Для user_id={user_id} выбран пол: {gender_db} (отображение: {gender_display})")

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
    log.info(f"FSM для user_id={user_id} переведен в состояние 'CharacterCreation.choosing_name'.")
    log.debug(f"Данные FSM в конце 'choose_gender_handler': {await state.get_data()}")


@router.message(CharacterCreation.choosing_name)
async def choosing_name_handler(m: Message, state: FSMContext, bot: Bot) -> None:
    """
    Обрабатывает ввод имени персонажа.

    Валидирует имя, и в случае успеха переводит FSM в состояние подтверждения.
    В случае ошибки — информирует пользователя.

    Args:
        m (Message): Входящее сообщение с именем.
        state (FSMContext): Состояние FSM.
        bot (Bot): Экземпляр бота.

    Returns:
        None
    """
    if not m.from_user:
        log.warning("Хэндлер 'choosing_name_handler' получил обновление без 'from_user'.")
        return

    name = m.text.strip()
    log.info(f"Хэндлер 'choosing_name_handler' вызван user_id={m.from_user.id}. Попытка установить имя: '{name}'")

    state_data = await state.get_data()
    message_content = state_data.get("message_content")
    user_id = state_data.get("user_id")

    if not all([message_content, user_id]):
        log.warning(f"Недостаточно данных в FSM для user_id={m.from_user.id} в 'choosing_name_handler'. Данные: {state_data}")
        return

    chat_id = message_content.get("chat_id")

    try:
        await bot.delete_message(chat_id=chat_id, message_id=m.message_id)
        log.debug(f"Сообщение {m.message_id} с именем от user_id={user_id} удалено.")
    except Exception as e:
        log.warning(f"Не удалось удалить сообщение {m.message_id} от user_id={user_id}: {e}")

    is_valid, error_msg = validate_character_name(name)

    if is_valid:
        log.info(f"Имя '{name}' для персонажа user_id={user_id} прошло валидацию.")
        await state.update_data(name=name)
        await state.set_state(CharacterCreation.confirm)
        log.info(f"FSM для user_id={user_id} переведен в состояние 'CharacterCreation.confirm'.")

        text = LobbyMessages.NewCharacter.FINAL_CONFIRMATION.format(name=name, gender=state_data.get('gender_display', ''))
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_content.get("message_id"),
            text=text,
            parse_mode='HTML',
            reply_markup=confirm_kb()
        )
    else:
        log.warning(f"Имя '{name}' для персонажа user_id={user_id} не прошло валидацию. Причина: {error_msg}")
        text = f"<b>⚠️ Ошибка:</b> {error_msg}\n\n{LobbyMessages.NewCharacter.NAME_INPUT}"
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_content.get("message_id"),
            text=text,
            parse_mode='HTML',
            reply_markup=None
        )
    log.debug(f"Данные FSM в конце 'choosing_name_handler': {await state.get_data()}")


@router.callback_query(CharacterCreation.confirm, F.data == "confirm")
async def confirm_creation_handler(call: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    """
    Обрабатывает финальное подтверждение создания персонажа.

    Сохраняет данные в БД, очищает FSM и инициирует начало туториала.

    Args:
        call (CallbackQuery): Callback от кнопки подтверждения.
        state (FSMContext): Состояние FSM.
        bot (Bot): Экземпляр бота.

    Returns:
        None
    """
    if not call.from_user:
        log.warning("Хэндлер 'confirm_creation_handler' получил обновление без 'from_user'.")
        return

    log.info(f"Хэндлер 'confirm_creation_handler' [confirm] вызван user_id={call.from_user.id}")
    await call.answer()

    state_data = await state.get_data()
    user_id = call.from_user.id
    char_id = state_data.get("char_id")
    name = state_data.get("name")
    gender_db = state_data.get("gender_db")

    if not all([char_id, name, gender_db]):
        log.error(f"Критическая ошибка: недостаточно данных в FSM для завершения создания персонажа user_id={user_id}. Данные: {state_data}")
        await state.clear()
        await error_msg_default(call=call)
        return

    await state.set_state(StartTutorial.start)
    log.info(f"FSM для user_id={user_id} переведен в состояние 'StartTutorial.start'.")

    char_update_dto = CharacterOnboardingUpdateDTO(name=name, gender=gender_db, game_stage="tutorial_stats")
    create_service = OnboardingService(user_id=user_id, char_id=char_id)
    await create_service.update_character_db(char_update_dto=char_update_dto)
    log.info(f"Данные персонажа {char_id} (имя, пол, стадия) обновлены в БД.")

    # Очищаем FSM, оставляя только ключевые данные.
    await state.set_data({
        "message_menu": state_data.get("message_menu"),
        "message_content": state_data.get("message_content"),
        "char_id": char_id
    })
    log.debug(f"FSM для user_id={user_id} очищен от временных данных создания.")

    message_content = state_data.get("message_content")

    await animate_message_sequence(
        message_to_edit=message_content,
        sequence=TutorialMessages.WAKING_UP_SEQUENCE,
        bot=bot,
        final_reply_markup=None
    )
    log.debug(f"Анимация 'пробуждения' для user_id={user_id} завершена.")

    text, kb = create_service.get_data_start(name=name, gender=state_data.get("gender_display"))
    await bot.edit_message_text(
        chat_id=message_content.get("chat_id"),
        message_id=message_content.get("message_id"),
        text=text,
        parse_mode='HTML',
        reply_markup=kb
    )
    log.debug(f"Отправлено стартовое сообщение туториала для user_id={user_id}.")
    log.debug(f"Данные FSM в конце 'confirm_creation_handler': {await state.get_data()}")
