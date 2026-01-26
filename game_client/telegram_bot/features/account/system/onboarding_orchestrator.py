from aiogram.types import User

from common.schemas.enums import CoreDomain
from common.schemas.onboarding import OnboardingUIPayloadDTO
from game_client.telegram_bot.base.base_orchestrator import BaseBotOrchestrator
from game_client.telegram_bot.base.view_dto import UnifiedViewDTO
from game_client.telegram_bot.features.account.client import AccountClient
from game_client.telegram_bot.features.account.system.onboarding_ui import OnboardingUI


class OnboardingOrchestrator(BaseBotOrchestrator):
    def __init__(self, client: AccountClient):
        super().__init__(expected_state=CoreDomain.ONBOARDING)
        self.client = client
        self.ui = OnboardingUI()

    async def render(self, payload) -> UnifiedViewDTO:
        """
        Entry point от Director при переходе в ONBOARDING.
        """
        if isinstance(payload, OnboardingUIPayloadDTO):
            return self._render_step(payload, update_menu=True)

        return UnifiedViewDTO()

    async def handle_onboarding_action(self, user: User, action: str, value: str | None) -> UnifiedViewDTO:
        """
        Обработка callback кнопок (set_gender, finalize).
        """
        char_id = await self.director.get_char_id()
        if not char_id:
            return UnifiedViewDTO()

        response = await self.client.onboarding_action(char_id, action, value)

        switch_result = await self.check_and_switch_state(response, fallback_payload=user)
        if switch_result:
            return switch_result

        if not response.payload:
            return UnifiedViewDTO()

        return self._render_step(response.payload, update_menu=False)

    async def handle_onboarding_text(self, user: User, text: str) -> UnifiedViewDTO:
        """
        Обработка текстового ввода (имя персонажа).
        """
        char_id = await self.director.get_char_id()
        if not char_id:
            return UnifiedViewDTO()

        response = await self.client.onboarding_action(char_id, "set_name", text)

        switch_result = await self.check_and_switch_state(response, fallback_payload=user)
        if switch_result:
            return switch_result

        if not response.payload:
            return UnifiedViewDTO()

        return self._render_step(response.payload, update_menu=False)

    def _render_step(self, payload: OnboardingUIPayloadDTO, update_menu: bool) -> UnifiedViewDTO:
        """
        Внутренний метод рендера шага.
        """
        content_view = self.ui.render_step(payload)
        menu_view = self.ui.render_menu() if update_menu else None

        return UnifiedViewDTO(menu=menu_view, content=content_view)
