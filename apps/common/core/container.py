from redis.asyncio import Redis

from apps.common.core.settings import settings
from apps.common.services.core_service import CombatManager, RedisService
from apps.common.services.core_service.manager.account_manager import AccountManager
from apps.common.services.core_service.manager.arena_manager import ArenaManager
from apps.common.services.core_service.manager.world_manager import WorldManager
from apps.game_core.game_service.world.game_world_service import GameWorldService
from apps.game_core.game_service.world.world_loader_service import WorldLoaderService


class AppContainer:
    def __init__(self):
        # Сохраняем настройки, чтобы было удобно обращаться
        self.settings = settings
        self.redis_client = Redis.from_url(
            # 3. ТЕПЕРЬ URL БЕРЕТСЯ ОТСЮДА (он сам собрался с паролем или без)
            self.settings.redis_url,
            decode_responses=True,
            # 4. И ПАРАМЕТРЫ ПУЛА ТОЖЕ БЕРЕМ ОТСЮДА
            max_connections=self.settings.redis_max_connections,
            socket_timeout=self.settings.redis_timeout,
            socket_connect_timeout=self.settings.redis_timeout,
        )

        self.redis_service = RedisService(self.redis_client)
        self.account_manager = AccountManager(self.redis_service)
        self.arena_manager = ArenaManager(self.redis_service)
        self.combat_manager = CombatManager(self.redis_service)
        self.world_manager = WorldManager(self.redis_service)
        self.game_world_service = GameWorldService(self.world_manager)
        self.world_loader_service = WorldLoaderService(self.world_manager)

    async def shutdown(self):
        """
        Gracefully shuts down all services and connections managed by the container.
        """
        # Close Redis client connection
        await self.redis_client.aclose()

        # Call shutdown methods of other services/managers here if they have any
        if hasattr(self.game_world_service, "shutdown"):
            await self.game_world_service.shutdown()
        # if hasattr(self.arena_manager, 'shutdown'):
        #     await self.arena_manager.shutdown()
        # ... and so on for other managers/services
