# apps/bot/handlers/callback/game/__init__.py
from aiogram import Router

from apps.bot.handlers.callback.game.exploration.navigation import router as navigation_router

from .arena import arena_router_group
from .combat import combat_router
from .exploration import exploration_router_group  # Новый импорт
from .hub_entry import router as hub_entry_router

game_router_group = Router(name="game_group")
game_router_group.include_routers(
    navigation_router,
    exploration_router_group,  # Добавлено
    combat_router,
    arena_router_group,
    hub_entry_router,
)
