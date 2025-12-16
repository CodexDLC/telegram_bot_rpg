from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
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
        Создает сессию для каждого события и передает ее в хэндлер.
        Управление транзакциями (commit/rollback) должно происходить
        внутри сервисов или Unit of Work, а не в middleware.
        """
        async with self.session_pool() as session:
            data["session"] = session
            return await handler(event, data)
