from aiogram import Router

from .combat_router import router as combat_router
from .navigation import router as navigation_router

game_router_group = Router(name="game_group")
game_router_group.include_routers(navigation_router, combat_router)
