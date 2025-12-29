from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from apps.bot.bot_container import BotContainer
from apps.bot.core_client import ExplorationClient
from apps.bot.core_client.arena_client import ArenaClient
from apps.bot.core_client.inventory_client import InventoryClient
from apps.bot.core_client.status_client import StatusClient
from apps.game_core.core_container import CoreContainer
from apps.game_core.modules.exploration.encounter_service import EncounterService
from apps.game_core.modules.exploration.exploration_orchestrator import ExplorationOrchestrator
from apps.game_core.modules.inventory.inventory_orchestrator import InventoryOrchestrator
from apps.game_core.modules.inventory.logic.inventory_session_manager import InventorySessionManager


class ContainerMiddleware(BaseMiddleware):
    def __init__(self, core_container: CoreContainer, bot_container: BotContainer):
        self.core_container = core_container
        self.bot_container = bot_container

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        # 1. Пробрасываем контейнеры
        data["core_container"] = self.core_container
        data["bot_container"] = self.bot_container
        data["container"] = self.core_container  # Alias for legacy code

        # 2. Пробрасываем Stateless Clients (из BotContainer)
        data["combat_rbc_client"] = self.bot_container.combat_rbc_client
        data["lobby_client"] = self.bot_container.lobby_client
        data["onboarding_client"] = self.bot_container.onboarding_client
        data["auth_client"] = self.bot_container.auth_client
        data["scenario_client"] = self.bot_container.scenario_client

        # 3. Пробрасываем Legacy Managers (из CoreContainer)
        # Это нужно для старых хендлеров, которые еще не перешли на клиентов
        data["account_manager"] = self.core_container.account_manager
        data["arena_manager"] = self.core_container.arena_manager
        data["combat_manager"] = self.core_container.combat_manager
        data["world_manager"] = self.core_container.world_manager
        data["redis_service"] = self.core_container.redis_service
        data["game_world_service"] = self.core_container.game_world_service

        # 4. Создаем Stateful Clients (Old Architecture)
        # Они требуют session, которая появляется только в контексте запроса
        if "session" in data:
            session = data["session"]

            # ArenaClient
            data["arena_client"] = ArenaClient(
                session=session,
                account_manager=self.core_container.account_manager,
                arena_manager=self.core_container.arena_manager,
                combat_manager=self.core_container.combat_manager,
            )

            # ExplorationClient
            encounter_service = EncounterService(session)
            expl_orchestrator = ExplorationOrchestrator(
                game_world_service=self.core_container.game_world_service,
                account_manager=self.core_container.account_manager,
                world_manager=self.core_container.world_manager,
                encounter_service=encounter_service,
                movement_service=self.core_container.movement_service,
            )
            data["exploration_client"] = ExplorationClient(orchestrator=expl_orchestrator)

            # InventoryClient
            inv_manager = InventorySessionManager(redis_service=self.core_container.redis_service, session=session)
            inv_orchestrator = InventoryOrchestrator(session_manager=inv_manager)
            data["inventory_client"] = InventoryClient(orchestrator=inv_orchestrator)

            # StatusClient
            data["status_client"] = StatusClient(session=session)

        return await handler(event, data)
