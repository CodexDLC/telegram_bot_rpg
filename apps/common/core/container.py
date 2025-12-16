from redis.asyncio import Redis

from apps.common.core.settings import settings
from apps.common.database.repositories.ORM.users_repo_orm import UsersRepoORM
from apps.common.database.session import async_engine, async_session_factory
from apps.common.services.core_service import CombatManager, RedisService
from apps.common.services.core_service.manager.account_manager import AccountManager
from apps.common.services.core_service.manager.arena_manager import ArenaManager
from apps.common.services.core_service.manager.world_manager import WorldManager
from apps.game_core.game_service.world.game_world_service import GameWorldService
from apps.game_core.game_service.world.world_loader_service import WorldLoaderService


class AppContainer:
    def __init__(self):
        # 1. Настройки
        self.settings = settings

        # 2. База данных (Postgres / Neon / SQLite)
        # Мы просто сохраняем ссылки на них, чтобы раздавать другим
        self.db_engine = async_engine
        self.db_session_factory = async_session_factory

        # 3. Redis
        self.redis_client = Redis.from_url(
            self.settings.redis_url,
            decode_responses=True,
            max_connections=self.settings.redis_max_connections,
            socket_timeout=self.settings.redis_timeout,
            socket_connect_timeout=self.settings.redis_timeout,
        )
        self.redis_service = RedisService(self.redis_client)

        # 4. Сервисы и Менеджеры (Синглтоны)
        self.account_manager = AccountManager(self.redis_service)
        self.arena_manager = ArenaManager(self.redis_service)
        self.combat_manager = CombatManager(self.redis_service)
        self.world_manager = WorldManager(self.redis_service)
        self.game_world_service = GameWorldService(self.world_manager)
        self.world_loader_service = WorldLoaderService(self.world_manager)

    async def shutdown(self):
        """
        Корректное завершение работы всех сервисов и соединений.
        """
        # Закрываем Redis
        await self.redis_client.aclose()

        # Закрываем соединение с Базой Данных
        await self.db_engine.dispose()

        # Вызываем shutdown у сервисов, если есть
        if hasattr(self.game_world_service, "shutdown"):
            await self.game_world_service.shutdown()

    # --- ХЕЛПЕРЫ ДЛЯ СОЗДАНИЯ РЕПОЗИТОРИЕВ ---
    # Так как репозиториям нужна ЖИВАЯ сессия (которая живет недолго),
    # мы не создаем их в __init__, а даем метод для их создания.

    def get_users_repo(self, session) -> UsersRepoORM:
        return UsersRepoORM(session)
