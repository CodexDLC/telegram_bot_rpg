# apps/common/core/container.py
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
    CombatBotOrchestrator,
    ExplorationBotOrchestrator,
    InventoryBotOrchestrator,
    StatusBotOrchestrator,
    # LobbyBotOrchestrator, # Если используется
    # OnboardingBotOrchestrator, # Если используется
    # ScenarioBotOrchestrator # Если используется
)
from apps.game_core.core_container import CoreContainer
from apps.game_core.modules.exploration.encounter_service import EncounterService
from apps.game_core.modules.exploration.exploration_orchestrator import ExplorationOrchestrator
from apps.game_core.modules.inventory.inventory_orchestrator import InventoryOrchestrator
from apps.game_core.modules.inventory.logic.inventory_session_manager import InventorySessionManager
from apps.game_core.system.factories.monster.encounter_pool_service import EncounterPoolService


class AppContainer:
    """
    Legacy Container for backward compatibility.
    Wraps CoreContainer and provides factory methods expected by old handlers.
    """

    def __init__(self):
        self.core_container = CoreContainer()

        # Proxy attributes for compatibility
        self.settings = self.core_container.settings
        self.db_engine = self.core_container.db_engine
        self.db_session_factory = self.core_container.db_session_factory
        self.redis_client = self.core_container.redis_client
        self.redis_service = self.core_container.redis_service
        self.account_manager = self.core_container.account_manager
        self.arena_manager = self.core_container.arena_manager
        self.combat_manager = self.core_container.combat_manager
        self.world_manager = self.core_container.world_manager
        self.game_world_service = self.core_container.game_world_service
        self.world_loader_service = self.core_container.world_loader_service
        self.movement_service = self.core_container.movement_service

    async def shutdown(self):
        await self.core_container.shutdown()

    # --- Factory Methods (Restored) ---

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
        return CombatRBCClient(self.core_container)

    def get_combat_bot_orchestrator(self, session: AsyncSession) -> CombatBotOrchestrator:
        client = self.get_combat_client(session)
        return CombatBotOrchestrator(client=client)

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

    # --- Restored Methods for Lobby/Onboarding/Scenario/Auth ---
    # These were likely used by handlers directly or via BotContainer proxies that failed

    def get_lobby_client(self, session: AsyncSession) -> LobbyClient:
        return LobbyClient(self.core_container)

    # def get_lobby_bot_orchestrator(self, session: AsyncSession) -> LobbyBotOrchestrator:
    #     client = self.get_lobby_client(session)
    #     return LobbyBotOrchestrator(lobby_client=client)

    def get_auth_client(self, session: AsyncSession) -> AuthClient:
        return AuthClient(self.core_container)

    # def get_auth_bot_orchestrator(self, session: AsyncSession) -> AuthBotOrchestrator:
    #     # ... implementation depends on AuthBotOrchestrator deps
    #     pass

    def get_scenario_client(self, session: AsyncSession) -> ScenarioClient:
        return ScenarioClient(self.core_container)

    # def get_scenario_bot_orchestrator(self, session: AsyncSession) -> ScenarioBotOrchestrator:
    #     client = self.get_scenario_client(session)
    #     return ScenarioBotOrchestrator(client=client, account_manager=self.account_manager)

    def get_onboarding_client(self, session: AsyncSession) -> OnboardingClient:
        return OnboardingClient(self.core_container)

    # def get_onboarding_bot_orchestrator(self, session: AsyncSession) -> OnboardingBotOrchestrator:
    #     client = self.get_onboarding_client(session)
    #     return OnboardingBotOrchestrator(client=client)
