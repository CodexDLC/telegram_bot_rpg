from loguru import logger as log
from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramBadRequest



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
            # Отправляем новое сообщение с подробностями.
            # Проверяем, есть ли у call.message, чтобы избежать ошибки, если его нет
            if call.message:
                await call.message.answer(
                    f"⚠️ {message_text}\n\nПожалуйста, попробуйте начать заново с команды /start",
                    # TODO: В будущем здесь будет reply_markup=get_error_reply_kb()
                )
                log.debug(f"Сообщение об ошибке успешно отправлено user_id={user_id}.")
            else:
                log.error(f"Не удалось отправить сообщение об ошибке для user_id={user_id}, так как call.message отсутствует.")
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
        await UIErrorHandler._error_msg_default(
            call,
            message_text=error_text
        )

    # --- Публичные методы для конкретных ошибок ---

    @staticmethod
    async def generic_error(call: CallbackQuery) -> None:
        """
        Общая ошибка "Что-то пошло не так".
        (Бывшая error_msg_default)
        """
        await UIErrorHandler._error_msg_default(
            call,
            message_text="Что-то пошло не так. Данные не найдены."
        )

    @staticmethod
    async def invalid_id(call: CallbackQuery) -> None:
        """
        Специализированная функция для ошибок, связанных с неверным ID из callback.
        (Бывшая error_int_id)
        """
        await UIErrorHandler._error_msg_default(
            call,
            message_text="Произошел сбой. ID персонажа не прошел валидацию."
        )

    @staticmethod
    async def char_id_not_found_in_fsm(call: CallbackQuery) -> None:
        """
        Вызывается, когда 'char_id' не найден в FSM (критическая ошибка состояния).
        """
        await UIErrorHandler._error_msg_default(
            call,
            message_text="Что-то пошло не так. Данные о персонаже утеряны из памяти (FSM)."
        )

    @staticmethod
    async def message_content_not_found_in_fsm(call: CallbackQuery) -> None:
        """
        Вызывается, когда 'message_content' (chat_id, message_id) не найден в FSM.
        """
        await UIErrorHandler._error_msg_default(
            call,
            message_text="Что-то пошло не так. Не удалось найти сообщение для редактирования."
        )

    @staticmethod
    async def callback_data_missing(call: CallbackQuery) -> None:
        """
        Вызывается, когда хэндлер ожидал данные от callback, но они не пришли.
        """
        await UIErrorHandler._error_msg_default(
            call,
            message_text="Произошел сбой. Данные (callback data) не были получены."
        )
