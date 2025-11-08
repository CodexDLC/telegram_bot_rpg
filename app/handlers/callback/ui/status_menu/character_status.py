# app/handlers/callback/ui/status_menu/character_status.py
import logging
import time
from typing import Optional

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
from app.services.helpers_module.callback_exceptions import UIErrorHandler as ERR
from app.services.ui_service.character_status_service import CharacterMenuUIService
from app.services.ui_service.helpers_ui.ui_tools import await_min_delay

router = Router(name="character_status_menu")
log = logging.getLogger(__name__)


async def status_menu_start_handler(
    state: FSMContext,
    bot: Bot,
    call: Optional[CallbackQuery] = None,
    explicit_char_id: Optional[int] = None,
    explicit_view_mode: Optional[str] = None,
    explicit_call_type: Optional[str] = None,
) -> None:
    """
    Основная логика отображения и обновления меню статуса персонажа.

    Центральный узел для управления меню статуса. Работает в двух режимах:
    1.  **Callback:** Вызывается из `status_menu_callback_handler` при нажатии
        на inline-кнопку.
    2.  **Прямой вызов:** Вызывается из другого кода (например, лобби) для
        инициализации меню.

    Args:
        state (FSMContext): Состояние FSM.
        bot (Bot): Экземпляр бота.
        call (Optional[CallbackQuery]): Входящий callback.
        explicit_char_id (Optional[int]): Явно переданный ID персонажа.
        explicit_view_mode (Optional[str]): Явно переданный режим отображения.
        explicit_call_type (Optional[str]): Явно переданный тип действия.

    Returns:
        None
    """
    start_time = time.monotonic()
    state_data = await state.get_data()

    # --- Определение режима работы и сбор данных ---
    if call:
        # Режим 1: Вызов через Callback.
        char_id = explicit_char_id
        view_mode = explicit_view_mode
        call_type = explicit_call_type
        user_id = call.from_user.id
        log.info(f"Хэндлер 'status_menu_start_handler' (режим Callback) вызван user_id={user_id}, char_id={char_id}, action={call_type}")
    else:
        # Режим 2: Прямой вызов (из лобби).
        char_id = state_data.get("char_id")
        user_id = state_data.get("user_id")
        call_type = "bio"  # По умолчанию показываем биографию
        view_mode = "lobby"
        log.info(f"Хэндлер 'status_menu_start_handler' (прямой вызов) для user_id={user_id}, char_id={char_id}")

    # --- Валидация ключевых данных ---
    if not char_id:
        log.warning(f"Не найден char_id для user_id={user_id} в 'status_menu_start_handler'.")
        if call: await ERR.invalid_id(call)
        return
    if not user_id:
        log.error(f"Критическая ошибка: user_id не найден в FSM или call для char_id={char_id}.")
        return

    # --- Инициализация Сервиса и данных ---
    char_menu_service = CharacterMenuUIService(char_id=char_id, call_type=call_type, view_mode=view_mode)
    bd_data_status = state_data.get("bd_data_status")

    # Оптимизация: перезагружаем данные, если их нет или они для другого персонажа.
    if bd_data_status is None or char_id != bd_data_status.get("id"):
        log.info(f"Кэш FSM для user_id={user_id} пуст или неактуален. Загрузка данных из БД для char_id={char_id}.")
        bd_data_status = await get_status_data_package(char_id=char_id, user_id=user_id)
        if bd_data_status is None:
            log.warning(f"Не удалось загрузить 'bd_data_status' для char_id={char_id}.")
            if call: await ERR.invalid_id(call)
            return
        await state.update_data(bd_data_status=bd_data_status)
        log.debug(f"Данные 'bd_data_status' для char_id={char_id} сохранены в FSM.")
    else:
        log.debug(f"Используются кэшированные данные 'bd_data_status' из FSM для char_id={char_id}.")

    # --- Подготовка сообщения ---
    message_content = state_data.get("message_content")
    character = await fsm_convector(bd_data_status.get("character"), "character")
    character_state = await fsm_convector(bd_data_status.get("character_stats"), "character_stats")
    text, kb = char_menu_service.staus_bio_message(character=character, stats=character_state)
    log.debug(f"Текст и клавиатура для char_id={char_id} сгенерированы.")

    # --- Логика Отправки/Редактирования ---
    try:
        if message_content is None:
            log.debug(f"Контентное сообщение для user_id={user_id} не найдено. Создание нового.")
            msg = None
            if call:
                msg = await call.message.answer(text=text, parse_mode='HTML', reply_markup=kb)
            elif user_id:
                msg = await bot.send_message(chat_id=user_id, text=text, parse_mode='HTML', reply_markup=kb)

            if msg:
                message_content = {"message_id": msg.message_id, "chat_id": msg.chat.id}
                await state.update_data(message_content=message_content, user_id=user_id)
                log.info(f"Создано новое контентное сообщение {msg.message_id} для user_id={user_id}.")
            else:
                log.error(f"Не удалось создать контентное сообщение для user_id={user_id} (нет call и user_id).")
        else:
            log.debug(f"Редактирование сообщения {message_content.get('message_id')} для user_id={user_id}.")
            await bot.edit_message_text(
                chat_id=message_content.get("chat_id"),
                message_id=message_content.get("message_id"),
                text=TEXT_AWAIT,
                parse_mode='HTML',
            )
            await await_min_delay(start_time, min_delay=1)
            await bot.edit_message_text(
                chat_id=message_content.get("chat_id"),
                message_id=message_content.get("message_id"),
                text=text,
                parse_mode='HTML',
                reply_markup=kb
            )
            log.debug("Сообщение успешно отредактировано.")

    except TelegramBadRequest as e:
        if "message is not modified" in str(e).lower():
            log.debug(f"Сообщение для user_id={user_id} не было изменено, пропуск.")
            if call: await call.answer("Нет изменений.")
        else:
            log.warning(f"Ошибка Telegram API при обновлении статуса для user_id={user_id}: {e}")
    except Exception as e:
        log.exception(f"Критическая ошибка в 'status_menu_start_handler' для user_id={user_id}: {e}")

    log.info(f"Работа 'status_menu_start_handler' для user_id={user_id} завершена.")


@router.callback_query(
    StatusMenuCallback.filter(F.action == "bio"),
    StateFilter(*FSM_CONTEX_CHARACTER_STATUS)
)
async def status_menu_callback_handler(
        call: CallbackQuery,
        state: FSMContext,
        bot: Bot,
        callback_data: StatusMenuCallback
) -> None:
    """
    Обработчик-обертка для кнопок меню статуса.

    Перехватывает callback, извлекает данные и передает их в основную
    логическую функцию `status_menu_start_handler`.

    Args:
        call (CallbackQuery): Входящий callback от кнопки.
        state (FSMContext): Состояние FSM.
        bot (Bot): Экземпляр бота.
        callback_data (StatusMenuCallback): Распарсенные данные из callback.

    Returns:
        None
    """
    if not call.from_user:
        log.warning("Хэндлер 'status_menu_callback_handler' получил обновление без 'from_user'.")
        return

    log.info(f"Хэндлер 'status_menu_callback_handler' [{callback_data.action}] вызван user_id={call.from_user.id}, char_id={callback_data.char_id}")
    await call.answer()

    try:
        await call.message.edit_text(TEXT_AWAIT, parse_mode="html")
        log.debug(f"Сообщение {call.message.message_id} изменено на 'Ожидайте...'")
    except TelegramBadRequest as e:
        if "message is not modified" in str(e).lower():
            log.debug("Сообщение 'Ожидайте...' уже установлено, пропуск.")
        else:
            raise

    # Передаем управление основной функции.
    await status_menu_start_handler(
        state=state,
        bot=bot,
        call=call,
        explicit_char_id=callback_data.char_id,
        explicit_view_mode=callback_data.view_mode,
        explicit_call_type=callback_data.action
    )
