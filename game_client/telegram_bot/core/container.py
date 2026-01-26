from redis.asyncio import Redis

from game_client.telegram_bot.core.config import BotSettings
from game_client.telegram_bot.features.account.client import AccountClient
from game_client.telegram_bot.features.arena.client import ArenaClient
from game_client.telegram_bot.features.arena.system.arena_bot_orchestrator import ArenaBotOrchestrator
from game_client.telegram_bot.features.arena.system.arena_ui_service import ArenaUIService
from game_client.telegram_bot.features.combat.client import CombatClient
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

    @property
    def arena(self) -> ArenaBotOrchestrator:
        """Фабрика для ArenaBotOrchestrator"""
        return ArenaBotOrchestrator(self.arena_client, ArenaUIService())

    async def shutdown(self):
        if self.redis_client:
            await self.redis_client.close()
