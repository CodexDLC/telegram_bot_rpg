from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from loguru import logger as log
from sqlalchemy.ext.asyncio import async_sessionmaker


class DbSessionMiddleware(BaseMiddleware):
    """
    Middleware для внедрения сессии SQLAlchemy в обработчики событий.
    """

    def __init__(self, session_pool: async_sessionmaker):
        self.session_pool = session_pool

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """
        Создает сессию для каждого события, передает ее в хэндлер и закрывает.
        """
        event_id = event.update_id if hasattr(event, "update_id") else "N/A"

        # Исправление: безопасное получение user_id
        user_id = "N/A"
        event_from_user = data.get("event_from_user")
        if event_from_user and hasattr(event_from_user, "id"):
            user_id = event_from_user.id

        log_context = f"event_id={event_id} user_id={user_id}"

        async with self.session_pool() as session:
            data["session"] = session
            try:
                result = await handler(event, data)
                await session.commit()
                log.trace(f"DbSession | status=committed {log_context}")
                return result
            except Exception:
                log.error(f"DbSession | status=rollback {log_context}", exc_info=True)
                await session.rollback()
                raise
