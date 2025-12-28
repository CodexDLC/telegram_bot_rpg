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
from apps.common.schemas_dto.scenario_dto import ScenarioPayloadDTO


class OnboardingBotOrchestrator(BaseBotOrchestrator):
    """
    Оркестратор онбординга.
    """

    def __init__(self, client: OnboardingClient):
        super().__init__(expected_state=GameState.ONBOARDING)
        self.client = client
        self.ui = OnboardingUIService()
        # Флаги для рендера
        self._update_menu = False
        self._clean_history = False

    async def process_entry_point(self, user: User) -> Any:
        """
        Вход в онбординг (например, из Лобби).
        """
        self._update_menu = True
        self._clean_history = True

        response = await self.client.get_state(user.id)
        return await self._process_response_internal(response)

    async def handle_text_input(self, user: User, text: str) -> Any:
        """
        Обработка текстового ввода (имя).
        """
        self._update_menu = False
        self._clean_history = False

        response = await self.client.send_action(user.id, "set_name", text)
        return await self._process_response_internal(response)

    async def handle_callback(self, user: User, action: str, value: Any = None) -> Any:
        """
        Обработка нажатия кнопок.
        """
        self._update_menu = False
        self._clean_history = False

        response = await self.client.send_action(user.id, action, value)
        return await self._process_response_internal(response)

    async def render(self, payload: Any) -> Any:
        """
        Рендер (вызывается Директором при смене сцены).
        """
        if isinstance(payload, User):
            return await self.process_entry_point(payload)

        if isinstance(payload, OnboardingViewDTO):
            self._update_menu = True
            self._clean_history = True
            return self._render_view(payload)

        # Если payload пустой (None), но мы знаем, что это вход (например, из Лобби без данных)
        # Мы не можем вызвать process_entry_point без User.
        # Но если мы здесь, значит Director вызвал нас.
        # Если fallback_payload сработал, то payload должен быть User.
        # Если payload все еще None, значит fallback не сработал или не был передан.

        return None

    async def _process_response_internal(self, response: CoreResponseDTO) -> Any:
        """
        Внутренний метод обработки ответа.
        """
        # 1. Проверка на смену стейта
        if response.header.current_state != self.expected_state:
            # Если мы переходим в Сценарий, нам нужно сохранить char_id
            if (
                response.header.current_state == GameState.SCENARIO
                and isinstance(response.payload, ScenarioPayloadDTO)
                and response.payload.extra_data
            ):
                char_id = response.payload.extra_data.get("char_id")
                if char_id:
                    await self.director.set_char_id(char_id)

            # Переключаем стейт
            return await self.director.set_scene(target_state=response.header.current_state, payload=response.payload)

        # 2. Рендер текущего стейта
        if isinstance(response.payload, OnboardingViewDTO):
            return self._render_view(response.payload)

        return None

    def _render_view(self, view_dto: OnboardingViewDTO) -> UnifiedViewDTO:
        view_result = self.ui.render(view_dto)

        menu_view = None
        if self._update_menu:
            from apps.bot.ui_service.helpers_ui.dto.ui_common_dto import ViewResultDTO

            # Создаем меню с кнопкой выхода
            kb_builder = InlineKeyboardBuilder()
            kb_builder.button(text="[🔙 Выйти из мира ]", callback_data=SystemCallback(action="logout").pack())

            menu_view = ViewResultDTO(text="🎭 <b>Создание персонажа</b>", kb=kb_builder.as_markup())

        return UnifiedViewDTO(menu=menu_view, content=view_result, clean_history=self._clean_history)
