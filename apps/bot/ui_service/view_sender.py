import contextlib

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from loguru import logger as log

from apps.bot.ui_service.base_service import BaseUIService
from apps.bot.ui_service.dto.view_dto import UnifiedViewDTO
from apps.bot.ui_service.helpers_ui.dto.ui_common_dto import ViewResultDTO
from apps.bot.ui_service.helpers_ui.dto_helper import FSM_CONTEXT_KEY


class ViewSender(BaseUIService):
    """
    Сервис-почтальон.
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
        # Работаем с копией данных контекста
        context_data = self.state_data.get(FSM_CONTEXT_KEY, {})

        # --- ЛОГИКА CLEAN HISTORY ---
        if view.clean_history:
            # 1. Сначала физически удаляем старые сообщения, пока мы помним их ID
            await self._delete_previous_interface()

            # 2. Теперь очищаем локальный контекст (забываем старые ID)
            context_data = {}
            # (Важно: мы не трогаем state.update_data здесь, мы запишем новые данные в конце)

        # --- ОБРАБОТКА MENU (Сначала Меню, чтобы оно было выше) ---
        old_menu_id = context_data.get("message_menu", {}).get("message_id")
        new_menu_id = await self._process_message(view_dto=view.menu, old_message_id=old_menu_id, log_prefix="MENU")

        # --- ОБРАБОТКА CONTENT (Потом Контент, чтобы он был ниже) ---
        old_content_id = context_data.get("message_content", {}).get("message_id")
        new_content_id = await self._process_message(
            view_dto=view.content, old_message_id=old_content_id, log_prefix="CONTENT"
        )

        # --- ОБНОВЛЕНИЕ FSM ---
        has_changes = False

        if new_menu_id and new_menu_id != old_menu_id:
            context_data["message_menu"] = {"chat_id": self.user_id, "message_id": new_menu_id}
            has_changes = True

        if new_content_id and new_content_id != old_content_id:
            context_data["message_content"] = {"chat_id": self.user_id, "message_id": new_content_id}
            has_changes = True

        # Если были изменения или мы чистили историю (надо записать чистый dict с новыми ID)
        if has_changes or view.clean_history:
            await self.state.update_data({FSM_CONTEXT_KEY: context_data})

    async def _delete_previous_interface(self):
        """
        Пытается удалить старые сообщения Menu и Content.
        """
        # Берем координаты через BaseUIService (он читает из self.state_data)
        menu_coords = self.get_message_menu_data()
        content_coords = self.get_message_content_data()

        # Удаляем Меню
        if menu_coords:
            chat_id, msg_id = menu_coords
            with contextlib.suppress(TelegramAPIError):
                await self.bot.delete_message(chat_id=chat_id, message_id=msg_id)

        # Удаляем Контент
        if content_coords:
            chat_id, msg_id = content_coords
            with contextlib.suppress(TelegramAPIError):
                await self.bot.delete_message(chat_id=chat_id, message_id=msg_id)

    async def _process_message(
        self, view_dto: ViewResultDTO | None, old_message_id: int | None, log_prefix: str
    ) -> int | None:
        # (Код без изменений: Logic Edit -> Exception -> Send New)
        if not view_dto:
            return old_message_id

        if old_message_id:
            # Пытаемся отредактировать. Если ошибка API (не найдено, не изменилось) - игнорируем и шлем новое.
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
