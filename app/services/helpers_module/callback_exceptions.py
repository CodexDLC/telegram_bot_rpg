# app/services/helpers_module/callback_exceptions.py
import logging
from typing import Optional

from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramBadRequest

from app.resources.game_data.skill_library import SKILL_UI_GROUPS_MAP

log = logging.getLogger(__name__)


async def error_msg_default(call: CallbackQuery, message_text: str = "Что-то пошло не так. Данные не найдены.") -> None:
    """
    Отправляет пользователю стандартизированное сообщение об ошибке.

    Пытается ответить на callback, чтобы убрать "часики", и отправляет
    новое сообщение в чат с текстом ошибки.

    Args:
        call (CallbackQuery): Callback, вызвавший ошибку.
        message_text (str): Текст сообщения об ошибке.
    """
    user_id = call.from_user.id
    log.warning(f"Отправка сообщения об ошибке по умолчанию для user_id={user_id}. Текст: '{message_text}'")
    try:
        # Отвечаем на callback, чтобы убрать "часики" на кнопке.
        await call.answer(text="Произошла ошибка", show_alert=True)
    except TelegramBadRequest as e:
        log.warning(f"Не удалось ответить на callback для user_id={user_id}: {e}")

    try:
        # Отправляем новое сообщение с подробностями.
        await call.message.answer(
            f"⚠️ {message_text}\n\nПожалуйста, попробуйте начать заново с команды /start",
            # TODO: В будущем здесь будет reply_markup=get_error_reply_kb()
        )
        log.debug(f"Сообщение об ошибке успешно отправлено user_id={user_id}.")
    except TelegramBadRequest as e:
        log.error(f"Не удалось отправить сообщение об ошибке для user_id={user_id}: {e}")


async def error_int_id(call: CallbackQuery) -> None:
    """
    Специализированная функция для ошибок, связанных с неверным ID.
    """
    await error_msg_default(call, message_text="Произошел сбой. ID персонажа не прошел валидацию.")





