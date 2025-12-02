# app/handlers/callback/login/char_creation.py
import time
from typing import Any, cast

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from app.resources.fsm_states.states import CharacterCreation, InGame
from app.resources.keyboards.inline_kb.loggin_und_new_character import confirm_kb
from app.resources.schemas_dto.character_dto import CharacterOnboardingUpdateDTO
from app.resources.schemas_dto.fsm_state_dto import SessionDataDTO
from app.resources.texts.game_messages.lobby_messages import LobbyMessages
from app.resources.texts.game_messages.tutorial_messages import TutorialMessages
from app.services.core_service.manager.account_manager import account_manager
from app.services.helpers_module.callback_exceptions import UIErrorHandler as Err
from app.services.helpers_module.dto_helper import FSM_CONTEXT_KEY
from app.services.helpers_module.game_validator import validate_character_name
from app.services.ui_service.helpers_ui.ui_animation_service import UIAnimationService
from app.services.ui_service.helpers_ui.ui_tools import await_min_delay
from app.services.ui_service.menu_service import MenuService
from app.services.ui_service.navigation_service import DEFAULT_SPAWN_POINT
from app.services.ui_service.new_character.onboarding_service import OnboardingService

router = Router(name="character_creation_fsm")


async def start_creation_handler(
    call: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    user_id: int,
    char_id: int,
    message_menu: dict[str, Any],
    session: AsyncSession,
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
        message_menu (dict[str, Any]): ID чата и сообщения для меню.

    Returns:
        None
    """
    log.info(f"Хэндлер 'start_creation_handler' вызван user_id={user_id}, char_id={char_id}")
    await call.answer()
    start_time = time.monotonic()

    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    session_context.update({"user_id": user_id, "char_id": char_id})
    await state.update_data({FSM_CONTEXT_KEY: session_context})

    # Инициализируем сервис меню для получения нужного текста и клавиатуры.
    ms = MenuService(game_stage="creation", state_data=await state.get_data(), session=session)
    text, kb = await ms.get_data_menu()
    log.debug("Данные для меню получены от MenuService.")

    await await_min_delay(start_time, min_delay=0.3)

    # Обновляем верхнее сообщение (меню).
    if not message_menu.get("chat_id") or not message_menu.get("message_id"):
        log.error(f"Некорректные данные 'message_menu' для user_id={user_id}: {message_menu}")
        await Err.generic_error(call=call)
        return
    await bot.edit_message_text(
        chat_id=message_menu["chat_id"],
        message_id=message_menu["message_id"],
        text=text,
        parse_mode="html",
        reply_markup=kb,
    )
    log.debug(f"Сообщение-меню {message_menu['message_id']} обновлено для user_id={user_id}.")

    # Создаем или обновляем нижнее сообщение (контент).
    await create_message_content_start_creation(user_id=user_id, call=call, state=state, bot=bot)

    # Устанавливаем следующее состояние FSM.
    await state.set_state(CharacterCreation.choosing_gender)
    log.info(f"FSM для user_id={user_id} переведен в состояние 'CharacterCreation.choosing_gender'.")
    log.debug(f"Данные FSM в конце 'start_creation_handler': {await state.get_data()}")


async def create_message_content_start_creation(call: CallbackQuery, state: FSMContext, user_id: int, bot: Bot) -> None:
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
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    message_content: dict[str, Any] | None = session_context.get("message_content")

    await await_min_delay(start_time, min_delay=0.3)

    if message_content is None:
        log.debug(f"Контентное сообщение для user_id={user_id} не найдено, создается новое.")
        if call.message:
            msg = await call.message.answer(text=text, parse_mode="html", reply_markup=kb)
            message_content = {"chat_id": msg.chat.id, "message_id": msg.message_id}
            session_context["message_content"] = message_content
            await state.update_data({FSM_CONTEXT_KEY: session_context})
            log.info(f"Создано новое контентное сообщение {msg.message_id} для user_id={user_id}.")
    else:
        log.debug(
            f"Контентное сообщение {message_content.get('message_id')} для user_id={user_id} будет отредактировано."
        )
        try:
            await bot.edit_message_text(
                chat_id=message_content["chat_id"],
                message_id=message_content["message_id"],
                text=text,
                parse_mode="html",
                reply_markup=kb,
            )
            log.debug("Контентное сообщение успешно отредактировано.")
        except TelegramAPIError as e:
            log.exception(f"Не удалось отредактировать контентное сообщение для user_id={user_id}: {e}")
            await Err.char_id_not_found_in_fsm(call=call)


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
    if not call.from_user or not call.data:
        log.warning("Хэндлер 'choose_gender_handler' получил обновление без 'from_user' или 'data'.")
        return

    gender_callback = call.data
    log.info(f"Хэндлер 'choose_gender_handler' [{gender_callback}] вызван user_id={call.from_user.id}")
    await call.answer()
    start_time = time.monotonic()

    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    user_id = session_context.get("user_id")
    char_id = session_context.get("char_id")
    message_content: dict[str, Any] | None = session_context.get("message_content")

    if not isinstance(user_id, int) or not isinstance(char_id, int) or not isinstance(message_content, dict):
        log.warning(
            f"Недостаточно данных в FSM для user_id={call.from_user.id} в 'choose_gender_handler'. Данные: {state_data}"
        )
        await Err.generic_error(call=call)
        return

    create_service = OnboardingService(user_id=user_id, char_id=char_id)
    text, gender_display, gender_db = create_service.get_data_start_gender(gender_callback=gender_callback)
    log.debug(f"Для user_id={user_id} выбран пол: {gender_db} (отображение: {gender_display})")

    await await_min_delay(start_time, min_delay=0.3)

    await bot.edit_message_text(
        chat_id=message_content["chat_id"],
        message_id=message_content["message_id"],
        text=text,
        parse_mode="html",
        reply_markup=None,
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
    if not m.from_user or not m.text:
        log.warning("Хэндлер 'choosing_name_handler' получил обновление без 'from_user' или 'text'.")
        return

    name = m.text.strip()
    log.info(f"Хэндлер 'choosing_name_handler' вызван user_id={m.from_user.id}. Попытка установить имя: '{name}'")

    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    message_content: dict[str, Any] | None = session_context.get("message_content")
    user_id = session_context.get("user_id")

    if not isinstance(message_content, dict) or not isinstance(user_id, int):
        log.warning(
            f"Недостаточно данных в FSM для user_id={m.from_user.id} в 'choosing_name_handler'. Данные: {state_data}"
        )
        return

    chat_id = message_content.get("chat_id")
    if not chat_id:
        return

    try:
        await bot.delete_message(chat_id=chat_id, message_id=m.message_id)
        log.debug(f"Сообщение {m.message_id} с именем от user_id={user_id} удалено.")
    except TelegramAPIError as e:
        log.warning(f"Не удалось удалить сообщение {m.message_id} от user_id={user_id}: {e}")

    is_valid, error_msg = validate_character_name(name)

    if is_valid:
        log.info(f"Имя '{name}' для персонажа user_id={user_id} прошло валидацию.")
        await state.update_data(name=name)
        await state.set_state(CharacterCreation.confirm)
        log.info(f"FSM для user_id={user_id} переведен в состояние 'CharacterCreation.confirm'.")

        text = LobbyMessages.NewCharacter.FINAL_CONFIRMATION.format(
            name=name, gender=state_data.get("gender_display", "")
        )
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_content.get("message_id"),
            text=text,
            parse_mode="HTML",
            reply_markup=confirm_kb(),
        )
    else:
        log.warning(f"Имя '{name}' для персонажа user_id={user_id} не прошло валидацию. Причина: {error_msg}")
        text = f"<b>⚠️ Ошибка:</b> {error_msg}\n\n{LobbyMessages.NewCharacter.NAME_INPUT}"
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_content.get("message_id"),
            text=text,
            parse_mode="HTML",
            reply_markup=None,
        )
    log.debug(f"Данные FSM в конце 'choosing_name_handler': {await state.get_data()}")


@router.callback_query(CharacterCreation.confirm, F.data == "confirm")
async def confirm_creation_handler(call: CallbackQuery, state: FSMContext, bot: Bot, session: AsyncSession) -> None:
    """
    Обрабатывает финальное подтверждение создания персонажа.

    Сохраняет данные в БД, очищает FSM и инициирует начало туториала.

    Args:
        call (CallbackQuery): Callback от кнопки подтверждения.
        state (FSMContext): Состояние FSM.
        bot (Bot): Экземпляр бота.
        session (AsyncSession): Сессия базы данных.

    Returns:
        None
    """
    if not call.from_user:
        log.warning("Хэндлер 'confirm_creation_handler' получил обновление без 'from_user'.")
        return

    log.info(f"Хэндлер 'confirm_creation_handler' [confirm] вызван user_id={call.from_user.id}")
    await call.answer()

    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    user_id = call.from_user.id
    char_id = session_context.get("char_id")
    name = state_data.get("name")
    gender_db = state_data.get("gender_db")
    gender_display = state_data.get("gender_display")

    if not all(
        [
            isinstance(char_id, int),
            isinstance(name, str),
            isinstance(gender_db, str),
            isinstance(gender_display, str),
        ]
    ):
        log.error(
            "Критическая ошибка: недостаточно данных в FSM для завершения создания персонажа "
            f"user_id={user_id}. Данные: {state_data}"
        )
        await state.clear()
        await Err.generic_error(call=call)
        return

    await state.set_state(InGame.navigation)
    log.info(f"FSM для user_id={user_id} переведен в состояние 'InGame.navigation'.")

    name_str: str = cast(str, name)
    safe_gender = cast(Any, gender_db)

    char_update_dto = CharacterOnboardingUpdateDTO(name=name_str, gender=safe_gender, game_stage="in_game")
    create_service = OnboardingService(user_id=user_id, char_id=char_id)

    await create_service.update_character_db(session=session, char_update_dto=char_update_dto)
    log.info(f"Данные персонажа {char_id} (имя, пол, стадия) обновлены в БД.")

    # 🔥 FIX: Устанавливаем начальную локацию в Redis
    await account_manager.update_account_fields(char_id, {"location_id": DEFAULT_SPAWN_POINT})
    log.info(f"Установлена начальная локация '{DEFAULT_SPAWN_POINT}' для char_id={char_id} в Redis.")

    message_menu = session_context.get("message_menu")
    message_content = session_context.get("message_content")

    # Очищаем FSM от временных данных, сохраняя только необходимое для туториала
    new_session_context = {
        "user_id": user_id,
        "char_id": char_id,
        "message_menu": message_menu,
        "message_content": message_content,
    }
    await state.set_data({FSM_CONTEXT_KEY: new_session_context})
    log.debug(f"FSM для user_id={user_id} очищен от временных данных создания.")

    if not isinstance(message_content, dict):
        log.error(f"message_content не является словарем для user_id={user_id}")
        await Err.generic_error(call)
        return

    session_dto = SessionDataDTO(**session_context)
    anim_service = UIAnimationService(bot=bot, message_data=session_dto)
    await anim_service.animate_sequence(sequence=TutorialMessages.WAKING_UP_SEQUENCE, final_kb=None)
    log.debug(f"Анимация 'пробуждения' для user_id={user_id} завершена.")

    if name and gender_display is not None:
        text, kb = create_service.get_data_start(name=name, gender=gender_display)
    else:
        text = "ошибка"
        kb = None
        await Err.generic_error(call=call)

    await bot.edit_message_text(
        chat_id=message_content.get("chat_id"),
        message_id=message_content.get("message_id"),
        text=text,
        parse_mode="HTML",
        reply_markup=kb,
    )
    log.debug(f"Отправлено стартовое сообщение туториала для user_id={user_id}.")
    log.debug(f"Данные FSM в конце 'confirm_creation_handler': {await state.get_data()}")
