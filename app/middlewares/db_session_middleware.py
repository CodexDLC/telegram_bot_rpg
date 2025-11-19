# app/middlewares/db_session_middleware.py
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import async_sessionmaker


class DbSessionMiddleware(BaseMiddleware):
    """
    Middleware для внедрения сессии базы данных в хэндлеры.
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
        Этот метод вызывается при КАЖДОМ событии (сообщение, кнопка).
        """
        async with self.session_pool() as session:
            data["session"] = session
            return await handler(event, data)
