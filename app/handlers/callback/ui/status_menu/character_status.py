# app/handlers/callback/ui/status_menu/character_status.py

from aiogram import Bot, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

# --- ОБЩИЕ ИМПОРТЫ ---
from app.resources.keyboards.status_callback import StatusNavCallback
from app.services.helpers_module.callback_exceptions import UIErrorHandler as Err
from app.services.helpers_module.dto_helper import FSM_CONTEXT_KEY, fsm_clean_core_state

# --- ИМПОРТЫ ДЛЯ ГЕНЕРАЦИИ 'text, kb' ---
from app.services.ui_service.status_menu.status_service import CharacterMenuUIService

router = Router(name="character_status_menu")


# =================================================================
# 2. ЕДИНАЯ ФУНКЦИЯ-ВОРКЕР (которую будут вызывать все)
# =================================================================
async def show_status_tab_logic(
    call: CallbackQuery, state: FSMContext, bot: Bot, char_id: int, key: str, session: AsyncSession
) -> None:
    """
    Единая функция-воркер для отображения любой вкладки 0-го уровня.

    Выполняет всю *общую* логику:
    1. Инициализирует *базовый* `CharacterMenuUIService`.
    2. Получает `message_data`.
    3. Вызывает *разную* логику (if/elif) для генерации `text` и `kb`.
    4. Отправляет *общее* сообщение `bot.edit_message_text`.
    """
    if not call.from_user:
        return

    user_id = call.from_user.id
    log.info(f"User {user_id}: Запуск `_show_status_tab_logic` для char_id={char_id}, key='{key}'.")

    # --- 1. ОБЩАЯ ЛОГИКА: Инициализация ---
    state_data = await state.get_data()

    callback_for_service = StatusNavCallback(key=key, char_id=char_id)

    try:
        ui_service = CharacterMenuUIService(callback_data=callback_for_service, state_data=state_data)
    except (ValueError, AttributeError, TypeError) as e:
        log.error(f"Ошибка инициализации CharacterMenuUIService для user {user_id}: {e}", exc_info=True)
        await Err.handle_exception(call, "Ошибка при инициализации интерфейса.")
        return

    message_data = ui_service.get_message_content_data()
    chat_id, message_id = None, None

    if message_data:
        chat_id, message_id = message_data
    elif call.message:
        log.warning(f"User {user_id}: message_content не найден. Будет создано новое сообщение.")
        chat_id = call.message.chat.id

    if not chat_id:
        log.error(f"Не удалось определить chat_id для user {user_id}.")
        await Err.handle_exception(call, "Не удалось определить чат для отправки сообщения.")
        return

    character = await ui_service.get_data_service(session)

    if not character:
        log.warning(f"Персонаж с char_id={char_id} не найден для user {user_id}.")
        await Err.handle_exception(call, "Не удалось найти данные персонажа.")
        return

    text, kb = None, None
    try:
        if key == "bio":
            log.debug(f"User {user_id}: Генерация вкладки 'bio'.")
            text, kb = ui_service.staus_bio_message(character=character)

        elif key == "skills":
            log.debug(f"User {user_id}: Генерация вкладки 'skills'.")
            result = ui_service.status_message_skill_message(character=character)
            if result:
                text, kb = result

        elif key == "stats":
            log.info(f"User {user_id}: Заглушка для 'Модификаторов' (stats) вызвана.")
            result = ui_service.status_message_modifier_message(character=character)
            if result:
                text, kb = result

        else:
            log.warning(f"Неизвестный ключ '{key}' в `show_status_tab_logic`. Показ 'bio'.")
            text, kb = ui_service.staus_bio_message(character=character)

    except (ValueError, AttributeError, TypeError, KeyError) as e:
        log.exception(f"Критическая ошибка при *генерации* вкладки '{key}' для user {user_id}: {e}")
        await Err.handle_exception(call, f"Ошибка при создании вкладки '{key}'.")
        return

    if not text or not kb:
        log.error(f"Не удалось сгенерировать text или kb для вкладки '{key}' user {user_id}.")
        await Err.handle_exception(call, f"Ошибка при создании вкладки '{key}'.")
        return

    # --- 6. ОБЩАЯ ЛОГИКА: Отправка сообщения ---
    try:
        if message_id is None:
            # СЛУЧАЙ ЛОББИ (message_content не было)
            log.debug(f"User {user_id}: Создание нового message_content...")

            # 1. Отправляем СРАЗУ готовый 'bio' (а не заглушку)
            msg = await bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML", reply_markup=kb)

            # 2. Сохраняем ID НОВОГО сообщения в FSM
            new_content = {"chat_id": msg.chat.id, "message_id": msg.message_id}
            current_data = await state.get_data()
            session_context = current_data.get(FSM_CONTEXT_KEY, {})
            session_context["message_content"] = new_content
            await state.update_data({FSM_CONTEXT_KEY: session_context})
            log.info(f"User {user_id}: Создано message_content (id: {msg.message_id}) и сохранено в FSM.")

        else:
            # ОБЫЧНЫЙ СЛУЧАЙ (нажатие на 'skills' или 'stats')
            log.debug(f"User {user_id}: Редактирование message_content (id: {message_id}).")

            await bot.edit_message_text(
                chat_id=chat_id, message_id=message_id, text=text, parse_mode="HTML", reply_markup=kb
            )

        log.info(f"Сообщение для вкладки '{key}' (char_id={char_id}) успешно обновлено для user {user_id}.")

    except TelegramAPIError as e:
        log.error(f"Ошибка при *отправке/редактировании* сообщения для user {user_id}: {e}", exc_info=True)


# =================================================================
# 1. ГЛАВНЫЙ ХЭНДЛЕР-РОУТЕР (УРОВЕНЬ 0)
# =================================================================
@router.callback_query(StatusNavCallback.filter())
async def status_menu_router_handler(
    call: CallbackQuery, state: FSMContext, bot: Bot, callback_data: StatusNavCallback, session: AsyncSession
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

    log.info(f"User {user_id} вызвал 'status_menu_router_handler' для char_id={char_id} с ключом: '{key}'.")

    # Отвечаем на call здесь, ОДИН РАЗ.
    await call.answer()

    try:
        # Очищаем FSM от старого UI-состояния (кроме "ядра")
        # и устанавливаем актуальный char_id.
        await fsm_clean_core_state(state=state, event_source=call)
        # await state.update_data(char_id=char_id)
        log.debug(f"FSM state cleaned and char_id set to {char_id} for user {user_id}.")
    except (ValueError, AttributeError, TypeError, KeyError) as e:
        log.error(f"Ошибка при очистке FSM для user {user_id}: {e}", exc_info=True)
        await Err.handle_exception(call, "Ошибка при обновлении состояния.")
        return

    # --- Вызов Воркера ---
    await show_status_tab_logic(call=call, state=state, bot=bot, char_id=char_id, key=key, session=session)
