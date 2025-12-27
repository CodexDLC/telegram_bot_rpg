from typing import Any

from aiogram.types import User
from aiogram.utils.keyboard import InlineKeyboardBuilder

from apps.bot.core_client.onboarding_client import OnboardingClient
from apps.bot.resources.keyboards.callback_data import SystemCallback
from apps.bot.ui_service.base_bot_orchestrator import BaseBotOrchestrator
from apps.bot.ui_service.dto.view_dto import UnifiedViewDTO
from apps.bot.ui_service.onboarding.onboarding_ui_service import OnboardingUIService
from apps.common.schemas_dto.core_response_dto import CoreResponseDTO
from apps.common.schemas_dto.game_state_enum import GameState
from apps.common.schemas_dto.onboarding_dto import OnboardingViewDTO


class OnboardingBotOrchestrator(BaseBotOrchestrator):
    """
    Оркестратор онбординга.
    """

    def __init__(self, client: OnboardingClient):
        super().__init__(expected_state=GameState.ONBOARDING)
        self.client = client
        self.ui = OnboardingUIService()

    async def process_entry_point(self, user: User) -> Any:
        """
        Вход в онбординг (например, из Лобби).
        """
        response = await self.client.get_state(user.id)
        # При входе обновляем меню и чистим историю
        return await self._process_response(response, user, update_menu=True, clean_history=True)

    async def handle_text_input(self, user: User, text: str) -> Any:
        """
        Обработка текстового ввода (имя).
        """
        response = await self.client.send_action(user.id, "set_name", text)
        return await self._process_response(response, user)

    async def handle_callback(self, user: User, action: str, value: Any = None) -> Any:
        """
        Обработка нажатия кнопок.
        """
        response = await self.client.send_action(user.id, action, value)
        return await self._process_response(response, user)

    async def render(self, payload: Any) -> Any:
        """
        Рендер (вызывается Директором при смене сцены).
        """
        if isinstance(payload, User):
            return await self.process_entry_point(payload)
        return None

    async def _process_response(
        self, response: CoreResponseDTO, user: User, update_menu: bool = False, clean_history: bool = False
    ) -> Any:
        """
        Обрабатывает ответ от Core.
        """
        if response.header.current_state != self.expected_state:
            return await self.director.set_scene(target_state=response.header.current_state, payload=response.payload)

        if isinstance(response.payload, OnboardingViewDTO):
            view_result = self.ui.render(response.payload)

            menu_view = None
            if update_menu:
                from apps.bot.ui_service.helpers_ui.dto.ui_common_dto import ViewResultDTO

                # Создаем меню с кнопкой выхода
                kb_builder = InlineKeyboardBuilder()
                kb_builder.button(text="[🔙 Выйти из мира ]", callback_data=SystemCallback(action="logout").pack())

                menu_view = ViewResultDTO(text="🎭 <b>Создание персонажа</b>", kb=kb_builder.as_markup())

            return UnifiedViewDTO(menu=menu_view, content=view_result, clean_history=clean_history)

        return None
