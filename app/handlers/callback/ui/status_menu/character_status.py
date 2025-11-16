# app/handlers/callback/ui/status_menu/character_status.py
from loguru import logger as log
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
from app.services.ui_service.status_menu.status_service import CharacterMenuUIService


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

    user_id = call.from_user.id
    log.info(f"User {user_id}: Запуск `_show_status_tab_logic` для char_id={char_id}, key='{key}'.")

    # --- 1. ОБЩАЯ ЛОГИКА: Инициализация ---
    state_data = await state.get_data()

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

    message_data = ui_service.get_message_content_data()
    chat_id, message_id = None, None

    if message_data:
        chat_id, message_id = message_data
    else:
        # Мы НЕ падаем. Мы просто логируем.
        log.warning(f"User {user_id}: message_content не найден. Будет создано новое сообщение.")
        # И запоминаем chat_id для отправки нового сообщения
        chat_id = call.message.chat.id

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
    try:
        if message_id is None:
            # СЛУЧАЙ ЛОББИ (message_content не было)
            log.debug(f"User {user_id}: Создание нового message_content...")

            # 1. Отправляем СРАЗУ готовый 'bio' (а не заглушку)
            msg = await bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode='HTML',
                reply_markup=kb
            )

            # 2. Сохраняем ID НОВОГО сообщения в FSM
            new_content = {"chat_id": msg.chat.id, "message_id": msg.message_id}
            await state.update_data(message_content=new_content)
            log.info(f"User {user_id}: Создано message_content (id: {msg.message_id}) и сохранено в FSM.")

        else:
            # ОБЫЧНЫЙ СЛУЧАЙ (нажатие на 'skills' или 'stats')
            log.debug(f"User {user_id}: Редактирование message_content (id: {message_id}).")

            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                parse_mode='HTML',
                reply_markup=kb
            )

        log.info(f"Сообщение для вкладки '{key}' (char_id={char_id}) успешно обновлено для user {user_id}.")

    except Exception as e:
        log.error(f"Ошибка при *отправке/редактировании* сообщения для user {user_id}: {e}", exc_info=True)


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