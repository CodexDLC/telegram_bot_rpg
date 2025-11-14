# app/handlers/callback/ui/status_menu/character_status.py
import logging
import time
from aiogram import Router, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

# --- ОБЩИЕ ИМПОРТЫ ---
from app.resources.keyboards.status_callback import StatusNavCallback
from app.services.helpers_module.DTO_helper import fsm_clean_core_state
from app.services.ui_service.helpers_ui.ui_tools import await_min_delay
from app.services.helpers_module.callback_exceptions import UIErrorHandler as Err
from app.resources.texts.ui_messages import TEXT_AWAIT

# --- ИМПОРТЫ ДЛЯ ГЕНЕРАЦИИ 'text, kb' ---
from app.services.ui_service.status_menu.character_status_service import CharacterMenuUIService

log = logging.getLogger(__name__)
router = Router(name="character_status_menu")


# =================================================================
# 2. ЕДИНАЯ ФУНКЦИЯ-ВОРКЕР (которую будут вызывать все)
# =================================================================
async def show_status_tab_logic(
        call: CallbackQuery,
        state: FSMContext,
        bot: Bot,
        char_id: int,
        key: str
) -> None:
    """
    Единая функция-воркер для отображения любой вкладки 0-го уровня.

    Выполняет всю *общую* логику:
    1. Инициализирует *базовый* `CharacterMenuUIService`.
    2. Получает `message_data`.
    3. Вызывает *разную* логику (if/elif) для генерации `text` и `kb`.
    4. Отправляет *общее* сообщение `bot.edit_message_text`.
    """
    start_time = time.monotonic()
    user_id = call.from_user.id
    log.info(f"User {user_id}: Запуск `_show_status_tab_logic` для char_id={char_id}, key='{key}'.")

    # --- 1. ОБЩАЯ ЛОГИКА: Инициализация ---
    state_data = await state.get_data()

    # Ставим "заглушку" о загрузке
    await call.message.edit_text(TEXT_AWAIT, parse_mode="html")

    callback_for_service = StatusNavCallback(key=key, char_id=char_id)

    try:
        ui_service = CharacterMenuUIService(
            char_id=char_id,
            callback_data=callback_for_service,
            state_data=state_data
        )
    except Exception as e:
        log.error(f"Ошибка инициализации CharacterMenuUIService для user {user_id}: {e}", exc_info=True)
        await Err.handle_exception(call, "Ошибка при инициализации интерфейса.")
        return

    # --- 4. ОБЩАЯ ЛОГИКА: Получение `message_data` ---
    message_data = ui_service.get_message_data()
    if not message_data:
        log.warning(f"Не удалось получить chat_id/message_id для user {user_id}.")
        await Err.message_content_not_found_in_fsm(call)
        return
    chat_id, message_id = message_data

    character = await ui_service.get_data_service()
    if not character:
        log.warning(f"Персонаж с char_id={char_id} не найден для user {user_id}.")
        await Err.handle_exception(call, "Не удалось найти данные персонажа.")
        return

    try:
        if key == "bio":
            log.debug(f"User {user_id}: Генерация вкладки 'bio'.")

            text, kb = ui_service.staus_bio_message(character=character)

        elif key == "skills":
            log.debug(f"User {user_id}: Генерация вкладки 'skills'.")

            text, kb = ui_service.status_message_skill_message(character=character)

        elif key == "stats":
            log.info(f"User {user_id}: Заглушка для 'Модификаторов' (stats) вызвана.")

            text, kb = ui_service.status_message_modifier_message(character=character)

        else:
            log.warning(f"Неизвестный ключ '{key}' в `show_status_tab_logic`. Показ 'bio'.")

            if not character:
                await Err.handle_exception(call, "Не удалось найти данные персонажа.")
                return

            text, kb = ui_service.staus_bio_message(character=character)

    except Exception as e:
        log.exception(f"Критическая ошибка при *генерации* вкладки '{key}' для user {user_id}: {e}")
        await Err.handle_exception(call, f"Ошибка при создании вкладки '{key}'.")
        return

    # --- 6. ОБЩАЯ ЛОГИКА: Отправка сообщения ---
    await await_min_delay(start_time, min_delay=0.5)

    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            parse_mode='HTML',
            reply_markup=kb
        )
        log.info(f"Сообщение для вкладки '{key}' (char_id={char_id}) успешно обновлено для user {user_id}.")
    except Exception as e:
        log.error(f"Ошибка при *отправке* сообщения для user {user_id}: {e}", exc_info=True)


# =================================================================
# 1. ГЛАВНЫЙ ХЭНДЛЕР-РОУТЕР (УРОВЕНЬ 0)
# =================================================================
@router.callback_query(StatusNavCallback.filter())
async def status_menu_router_handler(
        call: CallbackQuery,
        state: FSMContext,
        bot: Bot,
        callback_data: StatusNavCallback
) -> None:
    """
    Главный роутер для навигации по вкладкам 0-го уровня (Био, Статы, Навыки).

    Его ЕДИНСТВЕННАЯ задача - очистить FSM и вызвать воркер.
    """
    if not call.from_user:
        log.warning("Handler 'status_menu_router_handler' received update without 'from_user'.")
        return

    key = callback_data.key
    char_id = callback_data.char_id
    user_id = call.from_user.id

    log.info(
        f"User {user_id} вызвал 'status_menu_router_handler' для char_id={char_id} с ключом: '{key}'."
    )

    # Отвечаем на call здесь, ОДИН РАЗ.
    await call.answer()

    try:
        # Очищаем FSM от старого UI-состояния (кроме "ядра")
        # и устанавливаем актуальный char_id.
        await fsm_clean_core_state(state=state, event_source=call)
        await state.update_data(char_id=char_id)
        log.debug(f"FSM state cleaned and char_id set to {char_id} for user {user_id}.")
    except Exception as e:
        log.error(f"Ошибка при очистке FSM для user {user_id}: {e}", exc_info=True)
        await Err.handle_exception(call, "Ошибка при обновлении состояния.")
        return

    # --- Вызов Воркера ---
    await show_status_tab_logic(
        call=call,
        state=state,
        bot=bot,
        char_id=char_id,
        key=key
    )