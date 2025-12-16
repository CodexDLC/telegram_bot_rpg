from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message
from loguru import logger as log

from apps.common.core.settings import settings


class IsAdmin(BaseFilter):
    """
    Проверяет, является ли пользователь администратором.
    """

    async def __call__(self, event: Message | CallbackQuery) -> bool:
        user = event.from_user
        if not user:
            log.debug("AdminCheck | result=false reason='user not found in event'")
            return False

        is_admin = user.id in settings.admin_ids_list
        log.debug(f"AdminCheck | user_id={user.id} result={is_admin}")
        return is_admin
