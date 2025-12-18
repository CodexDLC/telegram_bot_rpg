from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from apps.common.database.session import get_async_session


class DbSessionMiddleware(BaseMiddleware):
    """
    Middleware для внедрения сессии SQLAlchemy в обработчики событий.
    Использует get_async_session для автоматического управления транзакциями (commit/rollback).
    """

    def __init__(self, session_pool):
        # session_pool здесь не используется напрямую, так как мы берем get_async_session,
        # но оставим его в __init__ для совместимости с DI, если он там передается.
        pass

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with get_async_session() as session:
            data["session"] = session
            return await handler(event, data)
