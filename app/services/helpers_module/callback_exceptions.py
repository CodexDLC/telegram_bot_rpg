from contextlib import suppress

from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.types import CallbackQuery
from loguru import logger as log

from app.resources.keyboards.reply_kb import get_error_recovery_kb


class UIErrorHandler:
    """
    Класс-утилита для отправки стандартизированных сообщений об ошибках
    пользователю в ответ на CallbackQuery.

    Все методы статические, чтобы класс не нужно было инициализировать.
    Вызов: `await UIErrorHandler.char_id_not_found_in_fsm(call)`
    """

    @staticmethod
    async def _error_msg_default(call: CallbackQuery, message_text: str) -> None:
        """
        Приватный базовый метод.
        Отправляет пользователю стандартизированное сообщение об ошибке.

        Пытается ответить на callback, чтобы убрать "часики", и отправляет
        новое сообщение в чат с текстом ошибки.

        Args:
            call (CallbackQuery): Callback, вызвавший ошибку.
            message_text (str): Текст сообщения об ошибке.
        """
        # Проверяем, что call и call.from_user существуют (защита)
        if not call or not call.from_user:
            log.error("UIErrorHandler._error_msg_default вызван без 'call' или 'call.from_user'")
            return

        user_id = call.from_user.id
        log.warning(f"Отправка сообщения об ошибке (UIErrorHandler) для user_id={user_id}. Текст: '{message_text}'")
        try:
            # Отвечаем на callback, чтобы убрать "часики" на кнопке.
            await call.answer(text="Произошла ошибка", show_alert=True)
        except TelegramBadRequest as e:
            log.warning(f"Не удалось ответить на callback для user_id={user_id}: {e}")

        try:
            if call.message:
                # 2. --- (ДОБАВИТЬ reply_markup) ---
                await call.message.answer(
                    f"⚠️ {message_text}\n\nПожалуйста, попробуйте начать заново с команды /start или кнопки 'Рестарт'.",
                    reply_markup=get_error_recovery_kb(),
                )
                log.debug(f"Сообщение об ошибке и Reply-клавиатура успешно отправлены user_id={user_id}.")
            else:
                log.error(
                    f"Не удалось отправить сообщение об ошибке для user_id={user_id}, так как call.message отсутствует."
                )
        except TelegramBadRequest as e:
            log.error(f"Не удалось отправить сообщение об ошибке для user_id={user_id}: {e}")

    # --- НОВЫЙ УНИВЕРСАЛЬНЫЙ МЕТОД ---
    @staticmethod
    async def handle_exception(call: CallbackQuery, error_text: str = "Произошла непредвиденная ошибка.") -> None:
        """
        Универсальный обработчик исключений.

        Args:
            call: Объект CallbackQuery.
            error_text: Описание ошибки для пользователя.
        """
        await UIErrorHandler._error_msg_default(call, message_text=error_text)

    # --- Публичные методы для конкретных ошибок ---

    @staticmethod
    async def generic_error(call: CallbackQuery) -> None:
        """
        Общая ошибка "Что-то пошло не так".
        (Бывшая error_msg_default)
        """
        await UIErrorHandler._error_msg_default(call, message_text="Что-то пошло не так. Данные не найдены.")

    @staticmethod
    async def invalid_id(call: CallbackQuery) -> None:
        """
        Специализированная функция для ошибок, связанных с неверным ID из callback.
        (Бывшая error_int_id)
        """
        await UIErrorHandler._error_msg_default(call, message_text="Произошел сбой. ID персонажа не прошел валидацию.")

    @staticmethod
    async def char_id_not_found_in_fsm(call: CallbackQuery) -> None:
        """
        Вызывается, когда 'char_id' не найден в FSM (критическая ошибка состояния).
        """
        await UIErrorHandler._error_msg_default(
            call, message_text="Что-то пошло не так. Данные о персонаже утеряны из памяти (FSM)."
        )

    @staticmethod
    async def message_content_not_found_in_fsm(call: CallbackQuery) -> None:
        """
        Вызывается, когда 'message_content' (chat_id, message_id) не найден в FSM.
        """
        await UIErrorHandler._error_msg_default(
            call, message_text="Что-то пошло не так. Не удалось найти сообщение для редактирования."
        )

    @staticmethod
    async def callback_data_missing(call: CallbackQuery) -> None:
        """
        Вызывается, когда хэндлер ожидал данные от callback, но они не пришли.
        """
        await UIErrorHandler._error_msg_default(
            call, message_text="Произошел сбой. Данные (callback data) не были получены."
        )

    @staticmethod
    async def access_denied(call: CallbackQuery) -> None:
        """
        Вызывается, когда пользователь пытается взаимодействовать с чужим UI.
        """
        # Защита: если call.from_user нет (редко, но бывает), просто логируем
        if not call.from_user:
            return

        log.info(f"Access denied for user {call.from_user.id}")

        with suppress(TelegramAPIError):
            # show_alert=True -> всплывающее окно с кнопкой "ОК"
            await call.answer("⛔ Это не твой интерфейс!", show_alert=True)
