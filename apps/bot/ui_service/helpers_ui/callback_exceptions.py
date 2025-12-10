from contextlib import suppress

from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.types import CallbackQuery
from loguru import logger as log

from apps.bot.resources.keyboards import get_error_recovery_kb


class UIErrorHandler:
    """
    Класс-утилита для отправки стандартизированных сообщений об ошибках
    пользователю в ответ на CallbackQuery.

    Все методы статические, что исключает необходимость инициализации класса.
    """

    @staticmethod
    async def _error_msg_default(call: CallbackQuery, message_text: str) -> None:
        """
        Приватный базовый метод для отправки стандартизированного сообщения об ошибке.

        Пытается ответить на callback, чтобы убрать "часики" на кнопке,
        и отправляет новое сообщение в чат с текстом ошибки и клавиатурой восстановления.

        Args:
            call: Объект CallbackQuery, вызвавший ошибку.
            message_text: Текст сообщения об ошибке для пользователя.
        """
        if not call or not call.from_user:
            log.error(
                "UIErrorHandler | status=failed reason='_error_msg_default called without call or call.from_user'"
            )
            return

        user_id = call.from_user.id
        log.warning(f"UIErrorHandler | event=sending_error_message user_id={user_id} message='{message_text}'")
        try:
            await call.answer(text="Произошла ошибка", show_alert=True)
        except TelegramBadRequest as e:
            log.warning(
                f"UIErrorHandler | status=failed reason='Could not answer callback' user_id={user_id} error='{e}'"
            )

        try:
            if call.message:
                await call.message.answer(
                    f"⚠️ {message_text}\n\nПожалуйста, попробуйте начать заново с команды /start или кнопки 'Рестарт'.",
                    reply_markup=get_error_recovery_kb(),
                )
                log.debug(f"UIErrorHandler | event=error_message_sent user_id={user_id}")
            else:
                log.error(f"UIErrorHandler | status=failed reason='call.message is missing' user_id={user_id}")
        except TelegramBadRequest as e:
            log.error(
                f"UIErrorHandler | status=failed reason='Could not send error message' user_id={user_id} error='{e}'"
            )

    @staticmethod
    async def handle_exception(call: CallbackQuery, error_text: str = "Произошла непредвиденная ошибка.") -> None:
        """
        Универсальный обработчик исключений, использующий `_error_msg_default`.

        Args:
            call: Объект CallbackQuery.
            error_text: Описание ошибки для пользователя.
        """
        await UIErrorHandler._error_msg_default(call, message_text=error_text)

    @staticmethod
    async def generic_error(call: CallbackQuery) -> None:
        """
        Отправляет общее сообщение об ошибке "Что-то пошло не так".

        Args:
            call: Объект CallbackQuery.
        """
        await UIErrorHandler._error_msg_default(call, message_text="Что-то пошло не так. Данные не найдены.")

    @staticmethod
    async def invalid_id(call: CallbackQuery) -> None:
        """
        Отправляет сообщение об ошибке, связанной с неверным идентификатором.

        Args:
            call: Объект CallbackQuery.
        """
        await UIErrorHandler._error_msg_default(call, message_text="Произошел сбой. ID персонажа не прошел валидацию.")

    @staticmethod
    async def char_id_not_found_in_fsm(call: CallbackQuery) -> None:
        """
        Отправляет сообщение об ошибке, когда `char_id` не найден в FSM.

        Args:
            call: Объект CallbackQuery.
        """
        await UIErrorHandler._error_msg_default(
            call, message_text="Что-то пошло не так. Данные о персонаже утеряны из памяти (FSM)."
        )

    @staticmethod
    async def message_content_not_found_in_fsm(call: CallbackQuery) -> None:
        """
        Отправляет сообщение об ошибке, когда `message_content` не найден в FSM.

        Args:
            call: Объект CallbackQuery.
        """
        await UIErrorHandler._error_msg_default(
            call, message_text="Что-то пошло не так. Не удалось найти сообщение для редактирования."
        )

    @staticmethod
    async def callback_data_missing(call: CallbackQuery) -> None:
        """
        Отправляет сообщение об ошибке, когда ожидаемые данные из callback не получены.

        Args:
            call: Объект CallbackQuery.
        """
        await UIErrorHandler._error_msg_default(
            call, message_text="Произошел сбой. Данные (callback data) не были получены."
        )

    @staticmethod
    async def access_denied(call: CallbackQuery) -> None:
        """
        Отправляет сообщение об отказе в доступе, когда пользователь пытается
        взаимодействовать с чужим UI.

        Args:
            call: Объект CallbackQuery.
        """
        if not call.from_user:
            log.warning("UIErrorHandler | status=failed reason='Access denied called without from_user'")
            return

        log.info(f"UIErrorHandler | event=access_denied user_id={call.from_user.id}")

        with suppress(TelegramAPIError):
            await call.answer("⛔ Это не твой интерфейс!", show_alert=True)
