from contextlib import AbstractAsyncContextManager

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.core.settings import settings
from apps.common.database.repositories.ORM.scenario_repository import ScenarioRepositoryORM
from apps.common.database.session import async_engine, async_session_factory, get_async_session
from apps.common.services.core_service import (
    AccountManager,
    ArenaManager,
    CombatManager,
    RedisService,
    WorldManager,
)

# from apps.game_core.game_service.combat.combat_core_orchestrator import CombatCoreOrchestrator
# from apps.game_core.game_service.combat.combat_initialization_service import CombatInitializationService
# from apps.game_core.game_service.combat.combat_runtime_service import CombatRuntimeService
from apps.game_core.game_service.core_router import CoreRouter
from apps.game_core.game_service.exploration.encounter_service import EncounterService
from apps.game_core.game_service.exploration.exploration_orchestrator import ExplorationOrchestrator
from apps.game_core.game_service.exploration.movement_service import MovementService
from apps.game_core.game_service.inventory.inventory_orchestrator import InventoryOrchestrator
from apps.game_core.game_service.inventory.logic.inventory_session_manager import InventorySessionManager
from apps.game_core.game_service.lobby.lobby_orchestrator import LobbyCoreOrchestrator
from apps.game_core.game_service.onboarding.onboarding_orchestrator import OnboardingCoreOrchestrator
from apps.game_core.game_service.scenario_orchestrator.logic.scenario_director import ScenarioDirector
from apps.game_core.game_service.scenario_orchestrator.logic.scenario_evaluator import ScenarioEvaluator
from apps.game_core.game_service.scenario_orchestrator.logic.scenario_formatter import ScenarioFormatter
from apps.game_core.game_service.scenario_orchestrator.logic.scenario_manager import ScenarioManager
from apps.game_core.game_service.scenario_orchestrator.scenario_core_orchestrator import ScenarioCoreOrchestrator
from apps.game_core.game_service.world.game_world_service import GameWorldService
from apps.game_core.game_service.world.world_loader_service import WorldLoaderService


class CoreContainer:
    """
    Контейнер Ядра (Game Core Layer + Data Layer).
    Содержит инфраструктуру, менеджеры и фабрики бизнес-логики.
    """

    def __init__(self):
        self.settings = settings

        # 1. Инфраструктура
        self.db_engine = async_engine
        self.db_session_factory = async_session_factory

        self.redis_client = Redis.from_url(
            self.settings.redis_url,
            decode_responses=True,
            max_connections=self.settings.redis_max_connections,
            socket_timeout=self.settings.redis_timeout,
            socket_connect_timeout=self.settings.redis_timeout,
        )
        self.redis_service = RedisService(self.redis_client)

        # 2. Менеджеры (Singleton)
        self.account_manager = AccountManager(self.redis_service)
        self.arena_manager = ArenaManager(self.redis_service)
        self.combat_manager = CombatManager(self.redis_service)
        self.world_manager = WorldManager(self.redis_service)

        # 3. Глобальные сервисы (Singleton)
        self.game_world_service = GameWorldService(self.world_manager)
        self.world_loader_service = WorldLoaderService(self.world_manager)

        self.movement_service = MovementService(
            world_manager=self.world_manager,
            account_manager=self.account_manager,
            game_world_service=self.game_world_service,
        )

    async def shutdown(self):
        await self.redis_client.aclose()
        await self.db_engine.dispose()
        if hasattr(self.game_world_service, "shutdown"):
            await self.game_world_service.shutdown()

    # --- Session Management ---

    def get_session_context(self) -> AbstractAsyncContextManager[AsyncSession]:
        """
        Возвращает контекстный менеджер сессии с авто-коммитом.
        """
        return get_async_session()

    # --- Router ---

    def get_core_router(self) -> CoreRouter:
        return CoreRouter(self)

    # --- Фабрики Core Orchestrators (Scoped) ---

    def get_scenario_core_orchestrator(self, session: AsyncSession) -> ScenarioCoreOrchestrator:
        repo = ScenarioRepositoryORM(session)
        manager = ScenarioManager(self.redis_service, repo, self.account_manager)
        evaluator = ScenarioEvaluator()
        director = ScenarioDirector(evaluator, manager)
        formatter = ScenarioFormatter()
        router = self.get_core_router()

        return ScenarioCoreOrchestrator(
            scenario_manager=manager,
            scenario_evaluator=evaluator,
            scenario_director=director,
            scenario_formatter=formatter,
            core_router=router,
        )

    def get_lobby_core_orchestrator(self, session: AsyncSession) -> LobbyCoreOrchestrator:
        return LobbyCoreOrchestrator(session=session, redis_service=self.redis_service)

    def get_onboarding_core_orchestrator(self, session: AsyncSession) -> OnboardingCoreOrchestrator:
        router = self.get_core_router()
        return OnboardingCoreOrchestrator(session=session, redis_service=self.redis_service, core_router=router)

    def get_inventory_core_orchestrator(self, session: AsyncSession) -> InventoryOrchestrator:
        session_manager = InventorySessionManager(redis_service=self.redis_service, session=session)
        return InventoryOrchestrator(session_manager=session_manager)

    def get_exploration_core_orchestrator(self, session: AsyncSession) -> ExplorationOrchestrator:
        encounter_service = EncounterService(session)
        return ExplorationOrchestrator(
            game_world_service=self.game_world_service,
            account_manager=self.account_manager,
            world_manager=self.world_manager,
            encounter_service=encounter_service,
            movement_service=self.movement_service,
        )

    # def get_combat_core_orchestrator(self, session: AsyncSession) -> CombatCoreOrchestrator:
    #     router = self.get_core_router()
    #
    #     # Создаем сервисы здесь (DI)
    #     init_service = CombatInitializationService(session, self.combat_manager, self.account_manager)
    #     runtime_service = CombatRuntimeService(self.combat_manager, self.account_manager)
    #
    #     return CombatCoreOrchestrator(
    #         init_service=init_service,
    #         runtime_service=runtime_service,
    #         core_router=router
    #     )
