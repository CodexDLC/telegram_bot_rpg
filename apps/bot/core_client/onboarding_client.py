from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.schemas_dto.core_response_dto import CoreResponseDTO
from apps.common.schemas_dto.onboarding_dto import OnboardingActionDTO, OnboardingViewDTO
from apps.common.services.core_service.redis_service import RedisService
from apps.game_core.game_service.onboarding.onboarding_orchestrator import OnboardingCoreOrchestrator


class OnboardingClient:
    """
    Клиент для взаимодействия с системой онбординга.
    """

    def __init__(self, session: AsyncSession, redis_service: RedisService):
        self._orchestrator = OnboardingCoreOrchestrator(session, redis_service)

    async def get_state(self, char_id: int) -> CoreResponseDTO[OnboardingViewDTO]:
        """
        Запрашивает текущее состояние онбординга.
        """
        return await self._orchestrator.get_state(char_id)

    async def send_action(self, char_id: int, action: str, value: Any | None = None) -> CoreResponseDTO:
        """
        Отправляет действие пользователя.
        """
        dto = OnboardingActionDTO(action=action, value=value)
        return await self._orchestrator.handle_action(char_id, dto)
