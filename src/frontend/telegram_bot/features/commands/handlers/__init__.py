from aiogram import Router

from src.frontend.telegram_bot.features.commands.handlers.logout_handler import router as logout_router
from src.frontend.telegram_bot.features.commands.handlers.router import router as commands_router

router = Router(name="commands_feature_router")

router.include_routers(
    commands_router,
    logout_router,
)
