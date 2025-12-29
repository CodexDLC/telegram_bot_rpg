from apps.bot.core_client.auth_client import AuthClient
from apps.bot.core_client.combat_rbc_client import CombatRBCClient
from apps.bot.core_client.lobby_client import LobbyClient
from apps.bot.core_client.onboarding_client import OnboardingClient
from apps.bot.core_client.scenario_client import ScenarioClient
from apps.bot.ui_service.lobby.lobby_bot_orchestrator import LobbyBotOrchestrator
from apps.bot.ui_service.onboarding.onboarding_bot_orchestrator import OnboardingBotOrchestrator
from apps.bot.ui_service.scenario.scenario_bot_orchestrator import ScenarioBotOrchestrator
from apps.game_core.core_container import CoreContainer


class BotContainer:
    """
    Контейнер UI-слоя (Frontend).
    Содержит клиентов, которые умеют общаться с Core (Backend).
    """

    def __init__(self, core_container: CoreContainer):
        self.core = core_container

        # Stateless Clients (New Architecture)
        self.combat_rbc_client = CombatRBCClient(self.core)
        self.lobby_client = LobbyClient(self.core)
        self.onboarding_client = OnboardingClient(self.core)
        self.auth_client = AuthClient(self.core)
        self.scenario_client = ScenarioClient(self.core)

    # --- Compatibility Methods (Adapters for Handlers) ---

    def get_combat_rbc_client(self) -> CombatRBCClient:
        return self.combat_rbc_client

    def get_lobby_bot_orchestrator(self) -> LobbyBotOrchestrator:
        return LobbyBotOrchestrator(self.lobby_client)

    def get_onboarding_bot_orchestrator(self) -> OnboardingBotOrchestrator:
        return OnboardingBotOrchestrator(self.onboarding_client)

    def get_scenario_bot_orchestrator(self) -> ScenarioBotOrchestrator:
        # Исправлено: ScenarioBotOrchestrator принимает только клиента
        return ScenarioBotOrchestrator(self.scenario_client)

    def get_auth_client(self) -> AuthClient:
        return self.auth_client
