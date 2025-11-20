# app/middlewares/db_session_middleware.py
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from loguru import logger as log
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
            try:
                result = await handler(event, data)
                # Если хэндлер отработал без ошибок, коммитим изменения
                await session.commit()
                log.trace("Сессия успешно закрыта с коммитом.")
                return result
            except Exception as e:
                # В случае любой ошибки откатываем изменения
                log.exception(f"Произошла ошибка в хэндлере, откатываем сессию. Ошибка: {e}")
                await session.rollback()
                # Пробрасываем ошибку дальше, чтобы ее могли обработать другие слои
                raise
