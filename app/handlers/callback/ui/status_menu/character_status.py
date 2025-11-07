# app/handlers/callback/ui/status_menu/character_status.py
import logging
import time
from typing import Union

from aiogram import Router, F, Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.resources.fsm_states.states import FSM_CONTEX_CHARACTER_STATUS
from app.resources.keyboards.callback_data import StatusMenuCallback
from app.resources.texts.ui_messages import TEXT_AWAIT
from app.services.helpers_module.DTO_helper import fsm_convector
from app.services.helpers_module.get_data_handlers.status_data_helper import get_status_data_package
from app.services.helpers_module.helper_id_callback import error_int_id, error_msg_default
from app.services.ui_service.character_status_service import CharacterMenuUIService
from app.services.ui_service.helpers_ui.ui_tools import await_min_delay

router = Router(name="character_status_menu")
log = logging.getLogger(__name__)


async def status_menu_start_handler(
    state: FSMContext,
    bot: Bot,
    call: Union[CallbackQuery, None] = None,
    explicit_char_id: int = None,
    explicit_view_mode: str = None,
    explicit_call_type: str = None,
):
    """
    Основная логика отображения и обновления меню статуса персонажа.

    Эта функция является центральным узлом для управления меню статуса.
    Она может работать в двух режимах:
    1.  **Режим Callback (call is not None):** Вызывается из обработчика
        `status_menu_callback_handler` при нажатии на inline-кнопку
        (например, "Биография").
    2.  **Режим прямого вызова (call is None):** Вызывается из других частей
        кода, например, из лобби (`select_character_handler`), чтобы
        инициализировать или обновить меню статуса без прямого действия
        от пользователя в этом меню.

    Args:
        state (FSMContext): Состояние FSM.
        bot (Bot): Экземпляр бота.
        call (Union[CallbackQuery, None], optional): Входящий callback, если
            функция вызвана через обработчик. Defaults to None.
        explicit_char_id (int, optional): ID персонажа, переданный явно.
        explicit_view_mode (str, optional): Режим отображения (e.g., "lobby"),
            переданный явно.
        explicit_call_type (str, optional): Тип действия (e.g., "bio"),
            переданный явно.

    Returns:
        None
    """
    log.info("status_menu_start_handler (ЛОГИКА) начал работу")
    state_data = await state.get_data()
    start_time = time.monotonic()

    # --- Определение режима работы и сбор данных ---
    if call:
        # Режим 1: Вызов через Callback. Данные приходят из аргументов.
        log.debug("Режим 1 (Callback)")
        char_id = explicit_char_id
        view_mode = explicit_view_mode
        call_type = explicit_call_type
        user_id = call.from_user.id
    else:
        # Режим 2: Прямой вызов (из лобби). Данные берутся из FSM.
        log.debug("Режим 2 (Лобби, call=None)")
        char_id = state_data.get("char_id")
        user_id = state_data.get("user_id")
        call_type = "bio"  # По умолчанию показываем биографию
        view_mode = "lobby"

    # --- Валидация ключевых данных ---
    if char_id is None:
        log.error("Ошибка: ID персонажа не найден.")
        if call: await error_int_id(call)
        return
    if user_id is None:
        log.error(f"Критическая ошибка: user_id не найден.")
        return

    # --- Инициализация Сервиса и данных ---
    char_menu_service = CharacterMenuUIService(char_id=char_id, call_type=call_type, view_mode=view_mode)
    bd_data_status = state_data.get("bd_data_status")

    # Оптимизация: перезагружаем данные из БД только если их нет в FSM,
    # или если они относятся к другому персонажу.
    if bd_data_status is None or char_id != bd_data_status.get("id"):
        if bd_data_status is not None:
            log.warning(f"Кэш FSM неактуален. Принудительная перезагрузка.")
        bd_data_status = await get_status_data_package(char_id=char_id, user_id=user_id)

    if bd_data_status is None:
        log.warning(f"bd_data_status не найден для char_id={char_id}.")
        if call: await error_msg_default(call)
        return

    # --- Подготовка сообщения ---
    message_content = state_data.get("message_content")
    character = await fsm_convector(bd_data_status.get("character"), "character")
    character_state = await fsm_convector(bd_data_status.get("character_stats"), "character_stats")
    text, kb = char_menu_service.staus_bio_message(character=character, stats=character_state)

    # --- Логика Отправки/Редактирования ---
    try:
        new_message_created = False
        if message_content is None:
            # Случай 1: Сообщения еще нет, нужно создать новое.
            log.debug("message_content=None. Требуется НОВОЕ сообщение.")
            msg = None
            if call:
                msg = await call.message.answer(text=text, parse_mode='HTML', reply_markup=kb)
            elif user_id:
                msg = await bot.send_message(chat_id=user_id, text=text, parse_mode='HTML', reply_markup=kb)
            else:
                log.error("Критическая ошибка: некуда отправлять сообщение (нет call и user_id).")
                return

            message_content = {"message_id": msg.message_id, "chat_id": msg.chat.id}
            new_message_created = True
        else:
            # Случай 2: Сообщение уже есть, редактируем его.
            log.debug("message_content=Есть. РЕДАКТИРУЕМ существующее сообщение.")
            await bot.edit_message_text(
                chat_id=message_content.get("chat_id"),
                message_id=message_content.get("message_id"),
                text=TEXT_AWAIT,
                parse_mode='HTML',
            )
            if start_time:
                await await_min_delay(start_time, min_delay=1)
            await bot.edit_message_text(
                chat_id=message_content.get("chat_id"),
                message_id=message_content.get("message_id"),
                text=text,
                parse_mode='HTML',
                reply_markup=kb
            )

        # --- Обновление FSM ---
        update_data = {"bd_data_status": bd_data_status, "user_id": user_id}
        if new_message_created:
            update_data["message_content"] = message_content
        await state.update_data(**update_data)

        log.info(f"status_menu_start_handler (ЛОГИКА) закончил свою работу")

    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            log.debug("Сообщение не изменилось, игнорируем.")
        else:
            log.warning(f"Неожиданная ошибка Telegram API: {e}")
    except Exception as e:
        log.exception(f"Критическая ошибка при обновлении статуса: {e}")


@router.callback_query(
    StatusMenuCallback.filter(F.action == "bio"),
    StateFilter(*FSM_CONTEX_CHARACTER_STATUS)
)
async def status_menu_callback_handler(
        call: CallbackQuery,
        state: FSMContext,
        bot: Bot,
        callback_data: StatusMenuCallback
):
    """
    Обработчик-обертка для кнопок меню статуса.

    Эта функция-обертка ловит callback'и от кнопок меню статуса
    (например, "Биография"), извлекает из них необходимые данные и
    передает их в основную логическую функцию `status_menu_start_handler`.
    Такой подход разделяет логику парсинга callback'ов и основную
    бизнес-логику отображения меню.

    Args:
        call (CallbackQuery): Входящий callback от кнопки.
        state (FSMContext): Состояние FSM.
        bot (Bot): Экземпляр бота.
        callback_data (StatusMenuCallback): Распарсенные данные из callback.

    Returns:
        None
    """
    log.debug(f"Получен [StatusMenuCallback(bio)]: {callback_data}")
    await call.answer()
    await call.message.edit_text(TEXT_AWAIT, parse_mode="html")

    # Передаем управление основной функции, явно передавая все параметры.
    await status_menu_start_handler(
        state=state,
        bot=bot,
        call=call,
        explicit_char_id=callback_data.char_id,
        explicit_view_mode=callback_data.view_mode,
        explicit_call_type=callback_data.action
    )
