from aiogram import Router

from src.frontend.telegram_bot.features.account.handlers.lobby_entry_handler import router as lobby_entry_router
from src.frontend.telegram_bot.features.account.handlers.lobby_handlers import router as lobby_router
from src.frontend.telegram_bot.features.account.handlers.onboarding_handlers import router as onboarding_router

router = Router(name="account_router")

router.include_routers(
    lobby_entry_router,
    lobby_router,
    onboarding_router,
)
