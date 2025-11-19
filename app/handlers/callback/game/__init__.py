from aiogram import Router

from .navigation import router as navigation_router

game_router_group = Router(name="game_group")
game_router_group.include_router(navigation_router)
