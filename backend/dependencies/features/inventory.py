from typing import Annotated

from fastapi import Depends

from backend.database.redis.manager.inventory_manager import InventoryManager
from backend.dependencies.base import RedisContainerDep
from backend.dependencies.internal.context import ContextAssemblerServiceDep
from backend.dependencies.internal.dispatcher import SystemDispatcherDep
from backend.domains.user_features.inventory.engine.dispatcher_bridge import InventoryDispatcherBridge
from backend.domains.user_features.inventory.engine.inventory_enricher import InventoryEnricher
from backend.domains.user_features.inventory.gateway.inventory_gateway import InventoryGateway
from backend.domains.user_features.inventory.services.inventory_service import InventoryService
from backend.domains.user_features.inventory.services.inventory_session_service import InventorySessionService


# --- 1. Managers ---
async def get_inventory_manager(container: RedisContainerDep) -> InventoryManager:
    return container.inventory


InventoryManagerDep = Annotated[InventoryManager, Depends(get_inventory_manager)]


# --- 2. Engines (Bridge, Enricher) ---
async def get_inventory_bridge(dispatcher: SystemDispatcherDep) -> InventoryDispatcherBridge:
    return InventoryDispatcherBridge(dispatcher)


InventoryDispatcherBridgeDep = Annotated[InventoryDispatcherBridge, Depends(get_inventory_bridge)]


async def get_inventory_enricher() -> InventoryEnricher:
    return InventoryEnricher()


InventoryEnricherDep = Annotated[InventoryEnricher, Depends(get_inventory_enricher)]


# --- 3. Domain Services ---
async def get_inventory_session_service(
    manager: InventoryManagerDep, assembler: ContextAssemblerServiceDep
) -> InventorySessionService:
    return InventorySessionService(manager, assembler)


InventorySessionServiceDep = Annotated[InventorySessionService, Depends(get_inventory_session_service)]


async def get_inventory_service(
    session_service: InventorySessionServiceDep, enricher: InventoryEnricherDep, bridge: InventoryDispatcherBridgeDep
) -> InventoryService:
    return InventoryService(session_service, enricher, bridge)


InventoryServiceDep = Annotated[InventoryService, Depends(get_inventory_service)]


# --- 4. Gateway ---
async def get_inventory_gateway(service: InventoryServiceDep) -> InventoryGateway:
    return InventoryGateway(service)


InventoryGatewayDep = Annotated[InventoryGateway, Depends(get_inventory_gateway)]
