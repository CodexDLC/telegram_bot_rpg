from redis.asyncio import Redis

from app.core.settings import settings
from app.services.core_service.manager.account_manager import AccountManager
from app.services.core_service.manager.arena_manager import ArenaManager
from app.services.core_service.manager.combat_manager import CombatManager
from app.services.core_service.manager.world_manager import WorldManager
from app.services.core_service.redis_service import RedisService
from app.services.game_service.game_world_service import GameWorldService


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

    async def close(self):
        await self.redis_client.aclose()
