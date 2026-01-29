from redis.asyncio import Redis

from game_client.telegram_bot.core.config import BotSettings
from game_client.telegram_bot.features.account.client import AccountClient
from game_client.telegram_bot.features.arena.client import ArenaClient
from game_client.telegram_bot.features.arena.system.arena_bot_orchestrator import ArenaBotOrchestrator
from game_client.telegram_bot.features.arena.system.arena_ui_service import ArenaUIService
from game_client.telegram_bot.features.combat.client import CombatClient
from game_client.telegram_bot.features.exploration.client import ExplorationClient
from game_client.telegram_bot.features.exploration.system.interaction_orchestrator import InteractionOrchestrator
from game_client.telegram_bot.features.exploration.system.navigation_orchestrator import NavigationOrchestrator
from game_client.telegram_bot.features.game_menu.client import MenuClient
from game_client.telegram_bot.features.game_menu.system.menu_orchestrator import MenuBotOrchestrator
from game_client.telegram_bot.features.game_menu.system.menu_ui_service import MenuUIService
from game_client.telegram_bot.features.inventory.client import InventoryClient
from game_client.telegram_bot.features.inventory.system.inventory_bot_orchestrator import InventoryBotOrchestrator
from game_client.telegram_bot.features.scenario.client import ScenarioClient


class BotContainer:
    """
    DI Container for Telegram Bot (Frontend).
    Содержит API-клиенты, настройки и Redis.
    Никакой бизнес-логики или доступа к БД.
    """

    def __init__(self, settings: BotSettings, redis_client: Redis):
        self.settings = settings
        self.redis_client = redis_client

        # --- API Clients (Gateways to Backend) ---
        self.account = AccountClient(
            base_url=settings.backend_api_url, api_key=settings.backend_api_key, timeout=settings.backend_api_timeout
        )
        self.combat = CombatClient(
            base_url=settings.backend_api_url, api_key=settings.backend_api_key, timeout=settings.backend_api_timeout
        )
        self.scenario = ScenarioClient(
            base_url=settings.backend_api_url, api_key=settings.backend_api_key, timeout=settings.backend_api_timeout
        )
        self.arena_client = ArenaClient(
            base_url=settings.backend_api_url, api_key=settings.backend_api_key, timeout=settings.backend_api_timeout
        )
        self.exploration_client = ExplorationClient(
            base_url=settings.backend_api_url, api_key=settings.backend_api_key, timeout=settings.backend_api_timeout
        )
        self.menu_client = MenuClient(
            base_url=settings.backend_api_url, api_key=settings.backend_api_key, timeout=settings.backend_api_timeout
        )
        self.inventory_client = InventoryClient(
            base_url=settings.backend_api_url, api_key=settings.backend_api_key, timeout=settings.backend_api_timeout
        )

    @property
    def arena(self) -> ArenaBotOrchestrator:
        """Фабрика для ArenaBotOrchestrator"""
        return ArenaBotOrchestrator(self.arena_client, ArenaUIService())

    @property
    def menu_orchestrator(self) -> MenuBotOrchestrator:
        """Фабрика для MenuBotOrchestrator"""
        return MenuBotOrchestrator(self.menu_client, MenuUIService())

    def inventory_orchestrator(self) -> InventoryBotOrchestrator:
        """Фабрика для InventoryBotOrchestrator"""
        return InventoryBotOrchestrator(self.inventory_client)

    # =========================================================================
    # Exploration Orchestrators
    # =========================================================================

    def get_navigation_orchestrator(self) -> NavigationOrchestrator:
        """Фабрика для NavigationOrchestrator (entry point)"""
        return NavigationOrchestrator(self.exploration_client)

    def get_interaction_orchestrator(self) -> InteractionOrchestrator:
        """Фабрика для InteractionOrchestrator"""
        return InteractionOrchestrator(self.exploration_client)

    async def shutdown(self):
        if self.redis_client:
            await self.redis_client.close()
