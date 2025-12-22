from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.schemas_dto.onboarding_dto import OnboardingResponseDTO
from apps.common.services.core_service.redis_service import RedisService
from apps.game_core.game_service.onboarding.onboarding_core_orchestrator import OnboardingCoreOrchestrator


class OnboardingClient:
    """
    Клиент-адаптер для взаимодействия UI-слоя с OnboardingCoreOrchestrator.
    Инкапсулирует создание оркестратора и предоставляет единый метод `handle`.
    """

    def __init__(self, session: AsyncSession, redis_service: RedisService):
        self._orchestrator = OnboardingCoreOrchestrator(session, redis_service)

    async def handle(self, action: str, **kwargs) -> OnboardingResponseDTO:
        """
        Универсальный метод для обработки всех действий онбординга.
        Проксирует вызов напрямую к OnboardingCoreOrchestrator.

        Args:
            action: Строковый идентификатор действия (например, "start", "set_gender").
            **kwargs: Дополнительные данные, необходимые для действия (char_id, name, gender и т.д.).

        Returns:
            DTO с текстом и кнопками для отображения пользователю.
        """
        return await self._orchestrator.handle(action, **kwargs)
