from aiogram import Router

from .inventory_consumable import router as inventory_consumable_router
from .inventory_equip import router as inventory_equip_router
from .inventory_item_details import router as inventory_details_router
from .inventory_main import router as inventory_main_router
from .inventory_quest import router as inventory_quest_router
from .inventory_resource import router as inventory_resource_router

inventory_group_router = Router(name="inventory_main_router")

inventory_group_router.include_routers(
    inventory_main_router,
    inventory_equip_router,
    inventory_resource_router,
    inventory_quest_router,
    inventory_details_router,
    inventory_consumable_router,
)
