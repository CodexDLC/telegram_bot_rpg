# app/handlers/callback/ui/status_menu/character_status.py
import logging
import time
from aiogram import Router, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.resources.keyboards.status_callback import StatusNavCallback
from app.services.helpers_module.DTO_helper import fsm_clean_core_state
from app.services.ui_service.helpers_ui.ui_tools import await_min_delay
from app.services.ui_service.status_menu.character_status_service import CharacterMenuUIService
from app.services.helpers_module.callback_exceptions import UIErrorHandler as err

log = logging.getLogger(__name__)
router = Router(name="character_status_menu")


@router.callback_query(StatusNavCallback.filter())
async def bio_tab_callback_handler(
        call: CallbackQuery,
        state: FSMContext,
        bot: Bot,
        callback_data: StatusNavCallback
) -> None:
    """
    Обрабатывает отображение вкладки "Биография" в меню статуса персонажа.

    Этот хэндлер является единой точкой входа для отображения основной
    информации о персонаже. Он срабатывает при нажатии на кнопку "Статус"
    в игровом меню или на кнопку с именем персонажа в лобби.

    Логика работы:
    1. Очищает FSM от предыдущих состояний UI.
    2. Инициализирует `CharacterMenuUIService`.
    3. Получает данные о персонаже и `message_content` из сервиса.
    4. Формирует и отправляет сообщение с биографией и навигационной клавиатурой.

    Args:
        call: Объект CallbackQuery, инициировавший вызов.
        state: Контекст состояния FSM для управления состоянием пользователя.
        bot: Экземпляр бота для взаимодействия с API Telegram.
        callback_data: Данные из callback-кнопки, содержащие `char_id` и `key`.
    """
    start_time = time.monotonic()
    if not call.from_user:
        log.warning("Handler 'bio_tab_callback_handler' received update without 'from_user'.")
        return

    user_id = call.from_user.id
    char_id = callback_data.char_id
    log.info(f"User {user_id} вызвал 'bio_tab_callback_handler' для char_id={char_id}.")
    await call.answer()

    try:
        # 1. Очистка FSM и установка актуального char_id
        await fsm_clean_core_state(state=state, event_source=call)
        await state.update_data(char_id=char_id)
        log.debug(f"FSM state cleaned and char_id set to {char_id} for user {user_id}.")
    except Exception as e:
        log.error(f"Ошибка при очистке FSM для user {user_id}: {e}", exc_info=True)
        await err.handle_exception(call, "Ошибка при обновлении состояния.")
        return

    state_data = await state.get_data()

    # 2. Инициализация UI сервиса
    try:
        ui_service = CharacterMenuUIService(
            char_id=char_id,
            callback_data=callback_data,
            state_data=state_data
        )
    except Exception as e:
        log.error(f"Ошибка инициализации CharacterMenuUIService для user {user_id}: {e}", exc_info=True)
        await err.handle_exception(call, "Ошибка при инициализации интерфейса.")
        return

    # 3. Получение данных
    character = await ui_service.get_data_service()
    if not character:
        log.warning(f"Персонаж с char_id={char_id} не найден для user {user_id}.")
        await err.handle_exception(call, "Не удалось найти данные персонажа.")
        return

    message_data = ui_service.get_message_data()
    if not message_data:
        log.warning(f"Не удалось получить chat_id/message_id для user {user_id}.")
        # В этом конкретном случае можно использовать специализированный обработчик
        await err.message_content_not_found_in_fsm(call)
        return
    chat_id, message_id = message_data

    # 4. Формирование и отправка сообщения
    text, kb = ui_service.staus_bio_message(character=character)

    await await_min_delay(start_time, min_delay=0.5)

    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            parse_mode='HTML',
            reply_markup=kb
        )
        log.info(f"Сообщение 'Биография' для char_id={char_id} успешно обновлено для user {user_id}.")
    except Exception as e:
        log.error(f"Ошибка при редактировании сообщения для user {user_id}: {e}", exc_info=True)
        # Здесь можно не отправлять сообщение об ошибке пользователю,
        # так как это может быть вызвано, например, повторным нажатием.
