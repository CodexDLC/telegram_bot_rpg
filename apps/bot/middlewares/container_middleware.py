from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from apps.bot.bot_container import BotContainer
from apps.bot.core_client.arena_client import ArenaClient
from apps.bot.core_client.combat_rbc_client import CombatRBCClient
from apps.common.core.container import AppContainer


class ContainerMiddleware(BaseMiddleware):
    def __init__(self, container: AppContainer, bot_container: BotContainer | None = None):
        self.container = container
        self.bot_container = bot_container

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        # Пробрасываем контейнеры
        data["container"] = self.container
        if self.bot_container:
            data["bot_container"] = self.bot_container

        # Старые зависимости
        data["account_manager"] = self.container.account_manager
        data["arena_manager"] = self.container.arena_manager
        data["combat_manager"] = self.container.combat_manager
        data["world_manager"] = self.container.world_manager
        data["redis_service"] = self.container.redis_service
        data["game_world_service"] = self.container.game_world_service

        # Новые зависимости
        if "session" in data:
            # data["exploration_ui_service"] = self.container.get_exploration_ui_service(data["session"]) # УДАЛЕНО: Не используется

            # Создаем и передаем ArenaClient
            data["arena_client"] = ArenaClient(
                session=data["session"],
                account_manager=self.container.account_manager,
                arena_manager=self.container.arena_manager,
                combat_manager=self.container.combat_manager,
            )

            # Создаем и передаем CombatRBCClient
            data["combat_rbc_client"] = CombatRBCClient(
                session=data["session"],
                account_manager=self.container.account_manager,
                combat_manager=self.container.combat_manager,
            )

            # Создаем и передаем ExplorationClient
            # Используем фабричный метод контейнера, так как ExplorationClient требует сложной инициализации (Orchestrator и т.д.)
            data["exploration_client"] = self.container.get_exploration_client(data["session"])

        return await handler(event, data)
