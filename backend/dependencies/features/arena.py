from typing import Annotated

from fastapi import Depends

from backend.database.redis.manager.account_manager import AccountManager
from backend.database.redis.manager.arena_manager import ArenaManager
from backend.dependencies.base import RedisContainerDep
from backend.dependencies.features.account import AccountSessionServiceDep
from backend.dependencies.internal.dispatcher import SystemDispatcherDep
from backend.domains.user_features.arena.gateway.arena_gateway import ArenaGateway
from backend.domains.user_features.arena.services.arena_service import ArenaService
from backend.domains.user_features.arena.services.arena_session_service import ArenaSessionService

# --- 0. Managers ---


async def get_arena_manager(container: RedisContainerDep) -> ArenaManager:
    return container.arena


ArenaManagerDep = Annotated[ArenaManager, Depends(get_arena_manager)]


async def get_account_manager(container: RedisContainerDep) -> AccountManager:
    return container.account


AccountManagerDep = Annotated[AccountManager, Depends(get_account_manager)]


# --- 1. Session Service ---


async def get_arena_session_service(
    arena_manager: ArenaManagerDep,
    account_manager: AccountManagerDep,
) -> ArenaSessionService:
    return ArenaSessionService(arena_manager, account_manager)


ArenaSessionServiceDep = Annotated[ArenaSessionService, Depends(get_arena_session_service)]


# --- 2. Domain Service ---


async def get_arena_service(
    session_service: ArenaSessionServiceDep,
    dispatcher: SystemDispatcherDep,
    account_service: AccountSessionServiceDep,
) -> ArenaService:
    return ArenaService(session_service, dispatcher, account_service)


ArenaServiceDep = Annotated[ArenaService, Depends(get_arena_service)]


# --- 3. Gateway ---


async def get_arena_gateway(service: ArenaServiceDep) -> ArenaGateway:
    return ArenaGateway(service)


ArenaGatewayDep = Annotated[ArenaGateway, Depends(get_arena_gateway)]
