from typing import Annotated

from fastapi import Depends

from backend.database.redis.manager.account_manager import AccountManager
from backend.dependencies.base import DbSessionDep, RedisContainerDep

# Импортируем правильную зависимость диспетчера
from backend.dependencies.internal.dispatcher import SystemDispatcherDep
from backend.domains.user_features.account.gateway.lobby_gateway import LobbyGateway
from backend.domains.user_features.account.gateway.login_gateway import LoginGateway
from backend.domains.user_features.account.gateway.onboarding_gateway import OnboardingGateway

# Gateways
from backend.domains.user_features.account.gateway.registration_gateway import RegistrationGateway
from backend.domains.user_features.account.services.account_session_service import AccountSessionService
from backend.domains.user_features.account.services.lobby_service import LobbyService
from backend.domains.user_features.account.services.login_service import LoginService
from backend.domains.user_features.account.services.onboarding_service import OnboardingService

# Services
from backend.domains.user_features.account.services.registration_service import RegistrationService

# --- 0. Core Account Services (Managers) ---


async def get_account_manager(container: RedisContainerDep) -> AccountManager:
    return container.account


AccountManagerDep = Annotated[AccountManager, Depends(get_account_manager)]


async def get_account_session_service(account_manager: AccountManagerDep) -> AccountSessionService:
    return AccountSessionService(account_manager)


AccountSessionServiceDep = Annotated[AccountSessionService, Depends(get_account_session_service)]


# --- 1. Domain Services ---


async def get_registration_service(session: DbSessionDep) -> RegistrationService:
    return RegistrationService(session)


RegistrationServiceDep = Annotated[RegistrationService, Depends(get_registration_service)]


async def get_onboarding_service(session: DbSessionDep, session_service: AccountSessionServiceDep) -> OnboardingService:
    return OnboardingService(session, session_service)


OnboardingServiceDep = Annotated[OnboardingService, Depends(get_onboarding_service)]


async def get_lobby_service(
    session: DbSessionDep, session_service: AccountSessionServiceDep, onboarding_service: OnboardingServiceDep
) -> LobbyService:
    return LobbyService(session, session_service, onboarding_service)


LobbyServiceDep = Annotated[LobbyService, Depends(get_lobby_service)]


async def get_login_service(session: DbSessionDep, session_service: AccountSessionServiceDep) -> LoginService:
    return LoginService(session, session_service)


LoginServiceDep = Annotated[LoginService, Depends(get_login_service)]


# --- 2. Gateways ---


async def get_registration_gateway(service: RegistrationServiceDep) -> RegistrationGateway:
    return RegistrationGateway(service)


RegistrationGatewayDep = Annotated[RegistrationGateway, Depends(get_registration_gateway)]


async def get_lobby_gateway(service: LobbyServiceDep) -> LobbyGateway:
    return LobbyGateway(service)


LobbyGatewayDep = Annotated[LobbyGateway, Depends(get_lobby_gateway)]


async def get_onboarding_gateway(service: OnboardingServiceDep) -> OnboardingGateway:
    return OnboardingGateway(service)


OnboardingGatewayDep = Annotated[OnboardingGateway, Depends(get_onboarding_gateway)]


async def get_login_gateway(
    service: LoginServiceDep,
    onboarding_gateway: OnboardingGatewayDep,
    dispatcher: SystemDispatcherDep,  # Используем импортированную зависимость
) -> LoginGateway:
    return LoginGateway(service, onboarding_gateway, dispatcher)


LoginGatewayDep = Annotated[LoginGateway, Depends(get_login_gateway)]
