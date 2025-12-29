from contextlib import AbstractAsyncContextManager
from typing import TYPE_CHECKING

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
from apps.game_core.modules.exploration.encounter_service import EncounterService
from apps.game_core.modules.exploration.exploration_orchestrator import ExplorationOrchestrator
from apps.game_core.modules.exploration.game_world_service import GameWorldService
from apps.game_core.modules.exploration.movement_service import MovementService
from apps.game_core.modules.inventory.inventory_orchestrator import InventoryOrchestrator
from apps.game_core.modules.inventory.logic.inventory_session_manager import InventorySessionManager
from apps.game_core.modules.lobby.lobby_orchestrator import LobbyCoreOrchestrator
from apps.game_core.modules.onboarding.onboarding_orchestrator import OnboardingCoreOrchestrator
from apps.game_core.modules.scenario_orchestrator.logic.scenario_director import ScenarioDirector
from apps.game_core.modules.scenario_orchestrator.logic.scenario_evaluator import ScenarioEvaluator
from apps.game_core.modules.scenario_orchestrator.logic.scenario_formatter import ScenarioFormatter
from apps.game_core.modules.scenario_orchestrator.logic.scenario_manager import ScenarioManager
from apps.game_core.modules.scenario_orchestrator.scenario_core_orchestrator import ScenarioCoreOrchestrator

# from apps.game_core.modules.combat.combat_core_orchestrator import CombatCoreOrchestrator
# from apps.game_core.modules.combat.combat_initialization_service import CombatInitializationService
# from apps.game_core.modules.combat.combat_runtime_service import CombatRuntimeService
from apps.game_core.system.core_router import CoreRouter
from apps.game_core.system.factories.world.world_loader_service import WorldLoaderService

if TYPE_CHECKING:
    from apps.game_core.modules.combat.combat_entry_orchestrator import CombatEntryOrchestrator
    from apps.game_core.modules.combat.combat_interaction_orchestrator import CombatInteractionOrchestrator
    from apps.game_core.modules.combat.combat_turn_orchestrator import CombatTurnOrchestrator
    from apps.game_core.modules.combat.session.combat_session_service import CombatSessionService


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

    # --- Combat Services (New Architecture) ---

    def _get_combat_session_service(self) -> "CombatSessionService":
        from apps.game_core.modules.combat.mechanics.combat_consumable_service import CombatConsumableService
        from apps.game_core.modules.combat.session.combat_session_service import CombatSessionService
        from apps.game_core.modules.combat.session.runtime.combat_turn_manager import CombatTurnManager
        from apps.game_core.modules.combat.session.runtime.combat_view_service import CombatViewService
        from apps.game_core.modules.combat.supervisor.task_dispatcher import LocalAsyncioDispatcher

        view_service = CombatViewService()  # Removed self.combat_manager argument

        # Создаем диспетчер задач (Local Asyncio)
        dispatcher = LocalAsyncioDispatcher(self.combat_manager, self.account_manager)

        turn_manager = CombatTurnManager(self.combat_manager, self.account_manager, dispatcher)
        consumable_service = CombatConsumableService(self.combat_manager)

        return CombatSessionService(
            account_manager=self.account_manager,
            combat_manager=self.combat_manager,
            turn_manager=turn_manager,
            view_service=view_service,
            consumable_service=consumable_service,
        )

    def get_combat_turn_orchestrator(self) -> "CombatTurnOrchestrator":
        from apps.game_core.modules.combat.combat_turn_orchestrator import CombatTurnOrchestrator

        session_service = self._get_combat_session_service()

        return CombatTurnOrchestrator(session_service)

    def get_combat_interaction_orchestrator(self) -> "CombatInteractionOrchestrator":
        from apps.game_core.modules.combat.combat_interaction_orchestrator import CombatInteractionOrchestrator

        session_service = self._get_combat_session_service()
        return CombatInteractionOrchestrator(session_service)

    def get_combat_entry_orchestrator(self, session: AsyncSession) -> "CombatEntryOrchestrator":
        from apps.game_core.modules.combat.combat_entry_orchestrator import CombatEntryOrchestrator
        from apps.game_core.modules.combat.session.initialization.combat_lifecycle_service import (
            CombatLifecycleService,
        )
        from apps.game_core.modules.combat.session.runtime.combat_view_service import CombatViewService

        lifecycle = CombatLifecycleService(self.combat_manager, self.account_manager)
        session_service = self._get_combat_session_service()
        view_service = CombatViewService()  # Removed self.combat_manager argument

        return CombatEntryOrchestrator(
            lifecycle_service=lifecycle, session_service=session_service, view_service=view_service, db_session=session
        )
