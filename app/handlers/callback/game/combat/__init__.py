"""
Главный роутер для всех событий в бою.
Собирает в себя все специализированные роутеры.
"""

from aiogram import Router

from .ability_handlers import ability_router
from .action_handlers import action_router
from .item_handlers import item_router
from .log_handlers import log_router
from .menu_handlers import menu_router
from .zone_handlers import zone_router

combat_router = Router(name="combat_router")
combat_router.include_routers(
    action_router,
    ability_router,
    item_router,
    menu_router,
    zone_router,
    log_router,
)
