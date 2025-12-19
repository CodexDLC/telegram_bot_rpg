from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from apps.bot.core_client.arena_client import ArenaClient
from apps.common.core.container import AppContainer


class ContainerMiddleware(BaseMiddleware):
    def __init__(self, container: AppContainer):
        self.container = container

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        # Старые зависимости
        data["account_manager"] = self.container.account_manager
        data["arena_manager"] = self.container.arena_manager
        data["combat_manager"] = self.container.combat_manager
        data["world_manager"] = self.container.world_manager
        data["redis_service"] = self.container.redis_service
        data["game_world_service"] = self.container.game_world_service

        # Новые зависимости
        if "session" in data:
            data["exploration_ui_service"] = self.container.get_exploration_ui_service(data["session"])
            # Создаем и передаем ArenaClient
            data["arena_client"] = ArenaClient(
                session=data["session"],
                account_manager=self.container.account_manager,
                arena_manager=self.container.arena_manager,
                combat_manager=self.container.combat_manager,
            )

        return await handler(event, data)
