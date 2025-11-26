from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

from app.core.config import ADMIN_IDS


class IsAdmin(BaseFilter):
    """
    Проверяет, входит ли пользователь в список администраторов.
    Работает и с Message, и с CallbackQuery.
    """

    async def __call__(self, event: Message | CallbackQuery) -> bool:
        user = event.from_user
        if not user:
            return False
        return user.id in ADMIN_IDS
