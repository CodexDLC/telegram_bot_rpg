from contextlib import suppress

from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.types import CallbackQuery
from loguru import logger as log

from apps.bot.resources.keyboards import get_error_recovery_kb


class UIErrorHandler:
    """
    Класс-утилита для отправки стандартизированных сообщений об ошибках
    пользователю в ответ на CallbackQuery.
    """

    @staticmethod
    async def _error_msg_default(call: CallbackQuery, message_text: str) -> None:
        """
        Приватный базовый метод для отправки стандартизированного сообщения об ошибке.
        """
        if not call or not call.from_user:
            log.error(
                "UIErrorHandler | status=failed reason='_error_msg_default called without call or call.from_user'"
            )
            return

        user_id = call.from_user.id
        log.warning(f"UIErrorHandler | event=sending_error_message user_id={user_id} message='{message_text}'")

        try:
            # Убираем "часики" с кнопки
            await call.answer(text="Произошла ошибка", show_alert=True)
        except TelegramBadRequest as e:
            log.warning(
                f"UIErrorHandler | status=failed reason='Could not answer callback' user_id={user_id} error='{e}'"
            )

        try:
            if call.message:
                # Отправляем новое сообщение с кнопкой восстановления (Рестарт)
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
    async def report_and_restart(call: CallbackQuery, message_text: str) -> None:
        """
        Метод для критических ошибок в бою/навигации.
        Логирует проблему и предлагает пользователю восстановить сессию (Рестарт).
        """
        await UIErrorHandler._error_msg_default(call, message_text=message_text)

    @staticmethod
    async def handle_exception(call: CallbackQuery, error_text: str = "Произошла непредвиденная ошибка.") -> None:
        """Универсальный обработчик исключений."""
        await UIErrorHandler._error_msg_default(call, message_text=error_text)

    @staticmethod
    async def generic_error(call: CallbackQuery) -> None:
        """Общая ошибка 'Данные не найдены'."""
        await UIErrorHandler._error_msg_default(call, message_text="Что-то пошло не так. Данные не найдены.")

    @staticmethod
    async def char_id_not_found_in_fsm(call: CallbackQuery) -> None:
        """Ошибка отсутствия char_id в FSM."""
        await UIErrorHandler._error_msg_default(
            call, message_text="Что-то пошло не так. Данные о персонаже утеряны из памяти (FSM)."
        )

    @staticmethod
    async def message_content_not_found_in_fsm(call: CallbackQuery) -> None:
        """Ошибка отсутствия данных о сообщении в FSM."""
        await UIErrorHandler._error_msg_default(
            call, message_text="Что-то пошло не так. Не удалось найти сообщение для редактирования."
        )

    @staticmethod
    async def access_denied(call: CallbackQuery) -> None:
        """Отказ в доступе (чужой интерфейс)."""
        if not call.from_user:
            return
        log.info(f"UIErrorHandler | event=access_denied user_id={call.from_user.id}")
        with suppress(TelegramAPIError):
            await call.answer("⛔ Это не твой интерфейс!", show_alert=True)
