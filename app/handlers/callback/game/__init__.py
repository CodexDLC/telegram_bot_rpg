from aiogram import Router

from .arena import arena_router_group
from .combat_router import router as combat_router
from .hub_entry import router as hub_entry_router
from .navigation import router as navigation_router

game_router_group = Router(name="game_group")
game_router_group.include_routers(navigation_router, combat_router, arena_router_group, hub_entry_router)
