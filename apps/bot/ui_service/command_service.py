# app/services/ui_service/command_service.py
import contextlib
import time

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, User
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger as log

from apps.bot.core_client.auth_client import AuthClient
from apps.bot.resources.texts.buttons_callback import Buttons
from apps.bot.resources.texts.ui_messages import START_GREETING
from apps.bot.ui_service.base_service import BaseUIService
from apps.bot.ui_service.dto.view_dto import MenuViewDTO
from apps.bot.ui_service.helpers_ui.dto_helper import FSM_CONTEXT_KEY, fsm_load_auto
from apps.bot.ui_service.helpers_ui.ui_tools import await_min_delay
from apps.common.schemas_dto import SessionDataDTO, UserUpsertDTO


class CommandService:
    """
    Сервис для обработки базовых команд, таких как /start.
    Отвечает за бизнес-логику (БД, очистка), но не за отправку сообщений.
    """

    def __init__(self, user: User) -> None:
        self.user = user
        self.user_dto = UserUpsertDTO(
            telegram_id=user.id,
            first_name=user.first_name,
            username=user.username,
            last_name=user.last_name,
            language_code=user.language_code,
            is_premium=bool(user.is_premium),
        )
        log.debug(f"Инициализирован {self.__class__.__name__} для user_id={user.id}.")

    async def prepare_start(self, state: FSMContext, bot: Bot, auth_client: AuthClient) -> MenuViewDTO:
        """
        Готовит сессию к старту:
        1. Чистит старый UI.
        2. Сбрасывает FSM.
        3. Создает/обновляет юзера в БД (через AuthClient).
        4. Возвращает DTO с текстом и клавиатурой для отправки.
        """
        start_time = time.monotonic()

        # 1. Очистка старого UI
        await self._cleanup_old_ui(state, bot)

        # 2. Сброс состояния
        await state.clear()
        log.debug(f"FSM | action=clear user_id={self.user.id}")

        # 3. Бизнес-логика (БД)
        await auth_client.upsert_user(self.user_dto)
        log.info(f"UserInit | status=upserted user_id={self.user.id}")

        # Небольшая задержка для плавности
        await await_min_delay(start_time, min_delay=0.3)

        # 4. Подготовка ответа
        text = START_GREETING.format(first_name=self.user.first_name)
        kb = self.get_start_menu_kb()

        return MenuViewDTO(text=text, keyboard=kb)

    async def _cleanup_old_ui(self, state: FSMContext, bot: Bot) -> None:
        """Удаляет старые сообщения меню, контента и ошибок."""
        try:
            session_data: SessionDataDTO | None = await fsm_load_auto(state, FSM_CONTEXT_KEY)

            state_data = await state.get_data()
            ui_service = BaseUIService(state_data=state_data)

            # 1. Удаление Меню
            menu_data = ui_service.get_message_menu_data()
            if menu_data:
                with contextlib.suppress(TelegramAPIError):
                    await bot.delete_message(chat_id=menu_data[0], message_id=menu_data[1])
                log.debug(f"UICleanup | message=menu_message id={menu_data[1]} user_id={self.user.id}")

            # 2. Удаление Контента
            content_data = ui_service.get_message_content_data()
            if content_data:
                with contextlib.suppress(TelegramAPIError):
                    await bot.delete_message(chat_id=content_data[0], message_id=content_data[1])
                log.debug(f"UICleanup | message=content_message id={content_data[1]} user_id={self.user.id}")

            # 3. Удаление Сообщения об ошибке
            if session_data and session_data.message_error:
                with contextlib.suppress(TelegramAPIError):
                    await bot.delete_message(
                        chat_id=session_data.message_error["chat_id"],
                        message_id=session_data.message_error["message_id"],
                    )
                log.debug(
                    f"UICleanup | message=error_message id={session_data.message_error['message_id']} user_id={self.user.id}"
                )

        except TelegramAPIError as e:
            log.warning(f"UICleanup | status=failed user_id={self.user.id} error='{e}'")

    def get_start_menu_kb(self) -> InlineKeyboardMarkup:
        """Генерирует клавиатуру для стартового меню."""
        kb = InlineKeyboardBuilder()
        for key, value in Buttons.START.items():
            kb.button(text=value, callback_data=key)
        kb.adjust(1)
        return kb.as_markup()
