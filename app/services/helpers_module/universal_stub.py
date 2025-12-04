from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from loguru import logger as log

from app.resources.keyboards.callback_data import ArenaQueueCallback


class UniversalStubService:
    """
    Сервис для отображения универсальной "заглушки" о разработке.
    """

    def __init__(self, text: str):
        self.text = text

    async def handle_callback(self, call: CallbackQuery, callback_data: ArenaQueueCallback):
        """
        Обрабатывает callback, показывая сообщение-заглушку с кнопкой "Назад".
        """
        if not call.from_user or not call.message:
            return

        if not isinstance(call.message, Message):
            await call.answer()
            return

        log.info(f"Stub | event=triggered user_id={call.from_user.id} text='{self.text}'")

        # Создаем callback для кнопки "Назад" в главное меню арены
        back_callback = ArenaQueueCallback(char_id=callback_data.char_id, action="menu_main").pack()

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data=back_callback)]]
        )
        await call.message.edit_text(self.text, reply_markup=keyboard)
        await call.answer()
