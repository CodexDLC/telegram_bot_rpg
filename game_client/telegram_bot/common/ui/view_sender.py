import contextlib

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from loguru import logger as log

from game_client.telegram_bot.common.dto.view_dto import UnifiedViewDTO, ViewResultDTO
from game_client.telegram_bot.common.resources.constants import KEY_UI_COORDS
from game_client.telegram_bot.common.ui.base_service import BaseUIService


class ViewSender(BaseUIService):
    """
    Сервис-почтальон.
    Отвечает за отправку и обновление сообщений (Menu и Content).
    Использует KEY_UI_COORDS для хранения ID сообщений.
    """

    def __init__(self, bot: Bot, state: FSMContext, state_data: dict, user_id: int):
        super().__init__(state_data, char_id=None)
        self.bot = bot
        self.state = state
        self.user_id = user_id

    async def send(self, view: UnifiedViewDTO):
        """
        Основной метод синхронизации UI.
        """
        # Читаем координаты из локального ключа
        ui_coords = self.state_data.get(KEY_UI_COORDS, {})

        # --- ЛОГИКА CLEAN HISTORY ---
        if view.clean_history:
            # 1. Сначала физически удаляем старые сообщения
            await self._delete_previous_interface(ui_coords)

            # 2. Очищаем локальный контекст
            ui_coords = {}

        # --- ОБРАБОТКА MENU ---
        old_menu_id = ui_coords.get("menu_msg_id")
        new_menu_id = await self._process_message(view_dto=view.menu, old_message_id=old_menu_id, log_prefix="MENU")

        # --- ОБРАБОТКА CONTENT ---
        old_content_id = ui_coords.get("content_msg_id")
        new_content_id = await self._process_message(
            view_dto=view.content, old_message_id=old_content_id, log_prefix="CONTENT"
        )

        # --- ОБНОВЛЕНИЕ FSM ---
        has_changes = False

        if new_menu_id and new_menu_id != old_menu_id:
            ui_coords["menu_msg_id"] = new_menu_id
            has_changes = True

        if new_content_id and new_content_id != old_content_id:
            ui_coords["content_msg_id"] = new_content_id
            has_changes = True

        # Если были изменения или мы чистили историю
        if has_changes or view.clean_history:
            await self.state.update_data({KEY_UI_COORDS: ui_coords})

    async def _delete_previous_interface(self, ui_coords: dict):
        """
        Пытается удалить старые сообщения Menu и Content.
        """
        menu_id = ui_coords.get("menu_msg_id")
        content_id = ui_coords.get("content_msg_id")

        if menu_id:
            with contextlib.suppress(TelegramAPIError):
                await self.bot.delete_message(chat_id=self.user_id, message_id=menu_id)

        if content_id:
            with contextlib.suppress(TelegramAPIError):
                await self.bot.delete_message(chat_id=self.user_id, message_id=content_id)

    async def _process_message(
        self, view_dto: ViewResultDTO | None, old_message_id: int | None, log_prefix: str
    ) -> int | None:
        if not view_dto:
            return old_message_id

        if old_message_id:
            with contextlib.suppress(TelegramAPIError):
                await self.bot.edit_message_text(
                    chat_id=self.user_id, message_id=old_message_id, text=view_dto.text, reply_markup=view_dto.kb
                )
                return old_message_id

        try:
            sent = await self.bot.send_message(chat_id=self.user_id, text=view_dto.text, reply_markup=view_dto.kb)
            return sent.message_id
        except TelegramAPIError as e:
            log.error(f"ViewSender [{log_prefix}]: Send error: {e}")
            return None
