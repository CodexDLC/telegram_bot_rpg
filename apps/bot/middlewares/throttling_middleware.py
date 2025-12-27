from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from redis.asyncio import Redis


class ThrottlingMiddleware(BaseMiddleware):
    """
    Мидлварь для защиты от спама (Throttling).
    Блокирует частые запросы от одного пользователя.
    """

    def __init__(self, redis: Redis, rate_limit: float = 1.0):
        self.redis = redis
        self.rate_limit = rate_limit

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user_id = None

        if isinstance(event, Message) and event.from_user or isinstance(event, CallbackQuery) and event.from_user:
            user_id = event.from_user.id

        if not user_id:
            return await handler(event, data)

        # Ключ троттлинга
        key = f"throttle:{user_id}"

        # Проверяем наличие ключа
        if await self.redis.exists(key):
            # Если заблокировано
            if isinstance(event, CallbackQuery):
                await event.answer("⏳ Не так быстро!", show_alert=False)
            return None  # Прерываем обработку

        # Устанавливаем ключ с TTL
        # Используем set с ex (expire), значение не важно
        await self.redis.set(key, "1", ex=int(self.rate_limit) or 1)

        return await handler(event, data)
