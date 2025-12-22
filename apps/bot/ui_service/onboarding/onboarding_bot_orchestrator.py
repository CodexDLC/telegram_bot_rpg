from typing import Any

from apps.bot.core_client.onboarding_client import OnboardingClient
from apps.bot.ui_service.onboarding.dto.onboarding_view_dto import OnboardingViewDTO
from apps.bot.ui_service.onboarding.onboarding_ui_service import OnboardingUIService


class OnboardingBotOrchestrator:
    """
    Оркестратор на стороне бота (Controller Layer).
    Связывает входящие запросы (Handler), бизнес-логику (Client) и отображение (UI Service).
    """

    def __init__(self, client: OnboardingClient, ui_service: OnboardingUIService | None = None):
        self.client = client
        # Если UI сервис не передан, создаем дефолтный
        self.ui_service = ui_service or OnboardingUIService()

        # Payload Factory: подготавливает аргументы для вызова бэкенда
        self._payload_factory = {
            "start": self._payload_start,
            "set_gender": self._payload_set_gender,
            "set_name": self._payload_set_name,
            "finalize": self._payload_finalize,
        }

    async def handle_request(
        self, char_id: int, action: str, value: Any = None, fsm_data: dict | None = None
    ) -> OnboardingViewDTO:
        """
        Главный метод обработки запроса.
        """
        fsm_data = fsm_data or {}

        # 1. Подготовка данных (Payload Construction)
        payload_func = self._payload_factory.get(action, self._payload_start)
        payload = payload_func(char_id, value, fsm_data)

        # 2. Вызов бэкенда (Business Logic Execution)
        response_dto = await self.client.handle(action, **payload)

        # 3. Рендеринг (View Rendering)
        return self.ui_service.render_view(response_dto, context=fsm_data)

    # --- Payload Builders (Подготовка аргументов для клиента) ---

    def _payload_start(self, char_id, value, fsm_data):
        return {}

    def _payload_set_gender(self, char_id, value, fsm_data):
        return {}

    def _payload_set_name(self, char_id, value, fsm_data):
        return {}

    def _payload_finalize(self, char_id, value, fsm_data):
        return {"char_id": char_id, "name": fsm_data.get("name"), "gender": fsm_data.get("gender")}
