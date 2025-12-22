from contextlib import suppress

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger as log

from apps.bot.resources.keyboards import get_error_recovery_kb
from apps.bot.ui_service.helpers_ui.dto_helper import FSM_CONTEXT_KEY, fsm_load_auto, fsm_store
from apps.common.schemas_dto import SessionDataDTO


class UIErrorHandler:
    """
    Класс-утилита для отправки стандартизированных сообщений об ошибках
    пользователю в ответ на CallbackQuery.
    """

    @staticmethod
    async def _error_msg_default(
        call: CallbackQuery, message_text: str, state: FSMContext | None = None, bot: Bot | None = None
    ) -> None:
        """
        Приватный базовый метод для отправки стандартизированного сообщения об ошибке.
        Поддерживает анти-спам режим, если переданы state и bot.
        """
        if not call or not call.from_user:
            log.error(
                "UIErrorHandler | status=failed reason='_error_msg_default called without call or call.from_user'"
            )
            return

        user_id = call.from_user.id
        log.warning(f"UIErrorHandler | event=sending_error_message user_id={user_id} message='{message_text}'")

        # 1. Пытаемся показать Alert (всплывашку)
        try:
            await call.answer(text="Произошла ошибка", show_alert=True)
        except TelegramBadRequest as e:
            log.warning(
                f"UIErrorHandler | status=failed reason='Could not answer callback' user_id={user_id} error='{e}'"
            )

        # 2. Работа с сообщением об ошибке
        if not call.message:
            log.error(f"UIErrorHandler | status=failed reason='call.message is missing' user_id={user_id}")
            return

        error_text_full = (
            f"⚠️ {message_text}\n\nПожалуйста, попробуйте начать заново с команды /start или кнопки 'Рестарт'."
        )
        kb = get_error_recovery_kb()  # Это ReplyKeyboardMarkup

        # Если у нас есть доступ к FSM, пытаемся удалить старое сообщение об ошибке и отправить новое
        # (Редактировать нельзя, так как Reply клавиатура идет только с новым сообщением)
        if state and bot:
            try:
                session_data: SessionDataDTO | None = await fsm_load_auto(state, FSM_CONTEXT_KEY)

                if not session_data:
                    session_data = SessionDataDTO(user_id=user_id)

                # Проверяем, есть ли уже сообщение об ошибке
                if session_data.message_error:
                    with suppress(TelegramAPIError):
                        # Удаляем старое сообщение об ошибке
                        await bot.delete_message(
                            chat_id=session_data.message_error["chat_id"],
                            message_id=session_data.message_error["message_id"],
                        )

                # Отправляем новое
                msg = await call.message.answer(error_text_full, reply_markup=kb)

                # Сохраняем ID нового сообщения
                session_data.message_error = {"chat_id": msg.chat.id, "message_id": msg.message_id}

                # Сохраняем обновленный DTO в FSM
                await state.update_data({FSM_CONTEXT_KEY: await fsm_store(session_data)})
                log.debug(f"UIErrorHandler | event=error_message_sent_and_saved user_id={user_id}")
                return

            except Exception as e:  # noqa: BLE001
                log.error(f"UIErrorHandler | status=fsm_error user_id={user_id} error='{e}'", exc_info=True)
                # Fallback к старой логике

        # Fallback: Если нет state/bot или произошла ошибка FSM -> просто шлем сообщение
        try:
            await call.message.answer(error_text_full, reply_markup=kb)
            log.debug(f"UIErrorHandler | event=error_message_sent_fallback user_id={user_id}")
        except TelegramBadRequest as e:
            log.error(
                f"UIErrorHandler | status=failed reason='Could not send error message' user_id={user_id} error='{e}'"
            )

    @staticmethod
    async def report_and_restart(
        call: CallbackQuery, message_text: str, state: FSMContext | None = None, bot: Bot | None = None
    ) -> None:
        """
        Метод для критических ошибок в бою/навигации.
        """
        await UIErrorHandler._error_msg_default(call, message_text=message_text, state=state, bot=bot)

    @staticmethod
    async def handle_exception(
        call: CallbackQuery,
        error_text: str = "Произошла непредвиденная ошибка.",
        state: FSMContext | None = None,
        bot: Bot | None = None,
    ) -> None:
        """Универсальный обработчик исключений."""
        await UIErrorHandler._error_msg_default(call, message_text=error_text, state=state, bot=bot)

    @staticmethod
    async def generic_error(call: CallbackQuery, state: FSMContext | None = None, bot: Bot | None = None) -> None:
        """Общая ошибка 'Данные не найдены'."""
        await UIErrorHandler._error_msg_default(
            call, message_text="Что-то пошло не так. Данные не найдены.", state=state, bot=bot
        )

    @staticmethod
    async def char_id_not_found_in_fsm(
        call: CallbackQuery, state: FSMContext | None = None, bot: Bot | None = None
    ) -> None:
        """Ошибка отсутствия char_id в FSM."""
        await UIErrorHandler._error_msg_default(
            call, message_text="Что-то пошло не так. Данные о персонаже утеряны из памяти (FSM).", state=state, bot=bot
        )

    @staticmethod
    async def message_content_not_found_in_fsm(
        call: CallbackQuery, state: FSMContext | None = None, bot: Bot | None = None
    ) -> None:
        """Ошибка отсутствия данных о сообщении в FSM."""
        await UIErrorHandler._error_msg_default(
            call,
            message_text="Что-то пошло не так. Не удалось найти сообщение для редактирования.",
            state=state,
            bot=bot,
        )

    @staticmethod
    async def access_denied(call: CallbackQuery) -> None:
        """Отказ в доступе (чужой интерфейс)."""
        if not call.from_user:
            return
        log.info(f"UIErrorHandler | event=access_denied user_id={call.from_user.id}")
        with suppress(TelegramAPIError):
            await call.answer("⛔ Это не твой интерфейс!", show_alert=True)
