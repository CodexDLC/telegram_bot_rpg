from sqlalchemy.ext.asyncio import AsyncSession

from apps.bot.core_client.auth_client import AuthClient
from apps.bot.core_client.combat_rbc_client import CombatRBCClient
from apps.bot.core_client.lobby_client import LobbyClient
from apps.bot.core_client.onboarding_client import OnboardingClient
from apps.bot.core_client.scenario_client import ScenarioClient
from apps.bot.ui_service.combat.combat_bot_orchestrator import CombatBotOrchestrator
from apps.bot.ui_service.lobby.lobby_bot_orchestrator import LobbyBotOrchestrator
from apps.bot.ui_service.onboarding.onboarding_bot_orchestrator import OnboardingBotOrchestrator
from apps.bot.ui_service.scenario.scenario_bot_orchestrator import ScenarioBotOrchestrator
from apps.game_core.core_container import CoreContainer


class BotContainer:
    """
    Контейнер Бота (Presentation Layer).
    Содержит UI Orchestrators и Clients.
    Зависит от CoreContainer (Bridge).
    """

    def __init__(self, core_container: CoreContainer):
        self.core = core_container

    # --- Clients ---

    def get_scenario_client(self) -> ScenarioClient:
        return ScenarioClient(core_container=self.core)

    def get_lobby_client(self) -> LobbyClient:
        return LobbyClient(core_container=self.core)

    def get_onboarding_client(self) -> OnboardingClient:
        return OnboardingClient(core_container=self.core)

    def get_auth_client(self) -> AuthClient:
        return AuthClient(core_container=self.core)

    def get_combat_rbc_client(self, session: AsyncSession) -> CombatRBCClient:
        return CombatRBCClient(
            session=session,
            account_manager=self.core.account_manager,
            combat_manager=self.core.combat_manager,
        )

    # --- Orchestrators ---

    def get_scenario_bot_orchestrator(self) -> ScenarioBotOrchestrator:
        client = self.get_scenario_client()
        return ScenarioBotOrchestrator(client=client)

    def get_lobby_bot_orchestrator(self) -> LobbyBotOrchestrator:
        client = self.get_lobby_client()
        return LobbyBotOrchestrator(lobby_client=client)

    def get_onboarding_bot_orchestrator(self) -> OnboardingBotOrchestrator:
        client = self.get_onboarding_client()
        return OnboardingBotOrchestrator(client=client)

    def get_combat_bot_orchestrator(self, session: AsyncSession) -> CombatBotOrchestrator:
        client = self.get_combat_rbc_client(session)
        return CombatBotOrchestrator(client=client)
