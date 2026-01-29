from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from loguru import logger as log


class UserValidationMiddleware(BaseMiddleware):
    """
    Middleware для валидации наличия пользователя в событии.
    Блокирует обработку событий без user (защита от ботов/системных событий).
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = None

        # Извлекаем user из разных типов событий
        if isinstance(event, (Message, CallbackQuery)):
            user = event.from_user

        # Если нет пользователя - блокируем
        if not user:
            log.warning(f"UserValidation: Event without user, skipping | event_type={type(event).__name__}")
            return None  # Прерываем обработку

        # Добавляем user в контекст (чтобы не извлекать повторно в хендлерах)
        data["user"] = user

        return await handler(event, data)
