from typing import TYPE_CHECKING, Any

from apps.common.schemas_dto.core_response_dto import CoreResponseDTO
from apps.common.schemas_dto.onboarding_dto import OnboardingViewDTO

if TYPE_CHECKING:
    from apps.game_core.core_container import CoreContainer


class OnboardingClient:
    """
    Клиент для взаимодействия с OnboardingCoreOrchestrator.
    """

    def __init__(self, core_container: "CoreContainer"):
        self.core = core_container

    async def get_state(self, user_id: int) -> CoreResponseDTO[OnboardingViewDTO]:
        """
        Получает текущее состояние онбординга.
        """
        async with self.core.get_session_context() as session:
            orchestrator = self.core.get_onboarding_core_orchestrator(session)
            return await orchestrator.get_state(user_id)

    async def send_action(self, user_id: int, action: str, value: Any = None) -> CoreResponseDTO[OnboardingViewDTO]:
        """
        Отправляет действие пользователя.
        """
        async with self.core.get_session_context() as session:
            orchestrator = self.core.get_onboarding_core_orchestrator(session)
            return await orchestrator.handle_action(user_id, action, value)
