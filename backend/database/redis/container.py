from redis.asyncio import Redis

# Managers
from backend.database.redis.manager.account_manager import AccountManager
from backend.database.redis.manager.combat_manager import CombatManager
from backend.database.redis.manager.context_manager import ContextRedisManager
from backend.database.redis.manager.scenario_manager import ScenarioManager
from backend.database.redis.redis_service import RedisService

# from backend.database.redis.manager.world_manager import WorldManager # TODO: Add when moved
# from backend.database.redis.manager.inventory_manager import InventoryManager # TODO: Add when moved


class RedisContainer:
    """
    Контейнер для всех Redis-менеджеров.
    Обеспечивает единую точку доступа к слою данных Redis.
    """

    def __init__(self, redis_client: Redis):
        # 1. Base Service (Wrapper)
        self.service = RedisService(redis_client)

        # 2. Managers
        self.account = AccountManager(self.service)
        self.combat = CombatManager(self.service)
        self.context = ContextRedisManager(self.service)
        self.scenario = ScenarioManager(self.service)

        # TODO: Initialize other managers
        # self.world = WorldManager(self.service)
        # self.inventory = InventoryManager(self.service)
