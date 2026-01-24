from redis.asyncio import Redis

from game_client.telegram_bot.core.config import BotSettings
from game_client.telegram_bot.features.combat.client import CombatClient


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
        self.combat = CombatClient(
            base_url=settings.backend_api_url, api_key=settings.backend_api_key, timeout=settings.backend_api_timeout
        )

        # TODO: Add other clients (Inventory, etc.)

    async def shutdown(self):
        if self.redis_client:
            await self.redis_client.close()
