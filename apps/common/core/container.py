# apps/common/core/container.py
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from apps.bot.core_client import (
    ArenaClient,
    AuthClient,
    CombatRBCClient,
    ExplorationClient,
    InventoryClient,
    LobbyClient,
    OnboardingClient,
    ScenarioClient,
    StatusClient,
)
from apps.bot.ui_service import (
    ArenaBotOrchestrator,
    AuthBotOrchestrator,
    CombatBotOrchestrator,
    ExplorationBotOrchestrator,
    InventoryBotOrchestrator,
    LobbyBotOrchestrator,
    OnboardingBotOrchestrator,
    ScenarioBotOrchestrator,
    StatusBotOrchestrator,
)
from apps.common.core.settings import settings
from apps.common.database.session import async_engine, async_session_factory
from apps.common.services.core_service import (
    AccountManager,
    ArenaManager,
    CombatManager,
    RedisService,
    WorldManager,
)
from apps.game_core.game_service.exploration.encounter_service import EncounterService
from apps.game_core.game_service.exploration.exploration_orchestrator import ExplorationOrchestrator
from apps.game_core.game_service.exploration.movement_service import MovementService
from apps.game_core.game_service.inventory.inventory_orchestrator import InventoryOrchestrator
from apps.game_core.game_service.inventory.logic.inventory_session_manager import InventorySessionManager
from apps.game_core.game_service.monster.encounter_pool_service import EncounterPoolService
from apps.game_core.game_service.world.game_world_service import GameWorldService
from apps.game_core.game_service.world.world_loader_service import WorldLoaderService


class AppContainer:
    def __init__(self):
        self.settings = settings
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
        self.account_manager = AccountManager(self.redis_service)
        self.arena_manager = ArenaManager(self.redis_service)
        self.combat_manager = CombatManager(self.redis_service)
        self.world_manager = WorldManager(self.redis_service)
        self.game_world_service = GameWorldService(self.world_manager)
        self.world_loader_service = WorldLoaderService(self.world_manager)

        # --- Сервисы, не зависящие от сессии ---
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

    # --- Хелперы для создания сервисов, требующих сессию ---
    def get_encounter_pool_service(self, session: AsyncSession) -> EncounterPoolService:
        return EncounterPoolService(session)

    def get_encounter_service(self, session: AsyncSession) -> EncounterService:
        return EncounterService(session)

    def get_exploration_orchestrator(self, session: AsyncSession) -> ExplorationOrchestrator:
        encounter_service = self.get_encounter_service(session)
        return ExplorationOrchestrator(
            game_world_service=self.game_world_service,
            account_manager=self.account_manager,
            world_manager=self.world_manager,
            encounter_service=encounter_service,
            movement_service=self.movement_service,
        )

    def get_exploration_client(self, session: AsyncSession) -> ExplorationClient:
        exploration_orchestrator = self.get_exploration_orchestrator(session)
        return ExplorationClient(orchestrator=exploration_orchestrator)

    def get_combat_client(self, session: AsyncSession) -> CombatRBCClient:
        """Создает клиент ядра для боя."""
        return CombatRBCClient(
            session=session, account_manager=self.account_manager, combat_manager=self.combat_manager
        )

    def get_combat_bot_orchestrator(self, session: AsyncSession) -> CombatBotOrchestrator:
        """Создает UI-оркестратор для бота."""
        client = self.get_combat_client(session)
        expl_client = self.get_exploration_client(session)

        return CombatBotOrchestrator(
            client=client,
            account_manager=self.account_manager,
            exploration_client=expl_client,
            arena_manager=self.arena_manager,
            combat_manager=self.combat_manager,
            world_manager=self.world_manager,
        )

    def get_arena_client(self, session: AsyncSession) -> ArenaClient:
        return ArenaClient(
            session=session,
            account_manager=self.account_manager,
            arena_manager=self.arena_manager,
            combat_manager=self.combat_manager,
        )

    def get_arena_bot_orchestrator(self, session: AsyncSession) -> ArenaBotOrchestrator:
        client = self.get_arena_client(session)
        expl_client = self.get_exploration_client(session)
        return ArenaBotOrchestrator(arena_client=client, exploration_client=expl_client)

    def get_exploration_bot_orchestrator(self, session: AsyncSession) -> ExplorationBotOrchestrator:
        expl_client = self.get_exploration_client(session)
        combat_client = self.get_combat_client(session)
        return ExplorationBotOrchestrator(exploration_client=expl_client, combat_client=combat_client)

    def get_inventory_client(self, session: AsyncSession) -> InventoryClient:
        # Создаем новую цепочку: Manager -> Core -> Client
        session_manager = InventorySessionManager(redis_service=self.redis_service, session=session)
        core_orchestrator = InventoryOrchestrator(session_manager=session_manager)
        return InventoryClient(orchestrator=core_orchestrator)

    def get_inventory_bot_orchestrator(self, session: AsyncSession) -> InventoryBotOrchestrator:
        client = self.get_inventory_client(session)
        return InventoryBotOrchestrator(inventory_client=client)

    def get_status_client(self, session: AsyncSession) -> StatusClient:
        return StatusClient(session=session)

    def get_status_bot_orchestrator(self, session: AsyncSession) -> StatusBotOrchestrator:
        client = self.get_status_client(session)
        return StatusBotOrchestrator(status_client=client)

    def get_lobby_client(self, session: AsyncSession) -> LobbyClient:
        # UPDATED: Передаем redis_service
        return LobbyClient(session=session, redis_service=self.redis_service)

    def get_lobby_bot_orchestrator(self, session: AsyncSession) -> LobbyBotOrchestrator:
        client = self.get_lobby_client(session)
        return LobbyBotOrchestrator(lobby_client=client)

    def get_auth_client(self, session: AsyncSession) -> AuthClient:
        # UPDATED: Передаем redis_service
        return AuthClient(session=session, redis_service=self.redis_service)

    def get_auth_bot_orchestrator(self, session: AsyncSession) -> AuthBotOrchestrator:
        expl_client = self.get_exploration_client(session)
        combat_client = self.get_combat_client(session)
        return AuthBotOrchestrator(
            session=session,
            account_manager=self.account_manager,
            combat_manager=self.combat_manager,
            arena_manager=self.arena_manager,
            world_manager=self.world_manager,
            exploration_client=expl_client,
            combat_client=combat_client,
        )

    def get_scenario_client(self, session: AsyncSession) -> ScenarioClient:
        # Клиент сам соберет все зависимости Core-слоя
        return ScenarioClient(session=session, redis_service=self.redis_service, account_manager=self.account_manager)

    def get_scenario_bot_orchestrator(self, session: AsyncSession) -> ScenarioBotOrchestrator:
        client = self.get_scenario_client(session)
        return ScenarioBotOrchestrator(client=client, account_manager=self.account_manager)

    def get_onboarding_client(self, session: AsyncSession) -> OnboardingClient:
        return OnboardingClient(session=session, redis_service=self.redis_service)

    def get_onboarding_bot_orchestrator(self, session: AsyncSession) -> OnboardingBotOrchestrator:
        client = self.get_onboarding_client(session)
        # ui_service создается внутри оркестратора по дефолту
        return OnboardingBotOrchestrator(client=client)
