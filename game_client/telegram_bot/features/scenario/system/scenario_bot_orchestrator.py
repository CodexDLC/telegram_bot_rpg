import contextlib
from typing import Any

from common.schemas.scenario import ScenarioPayloadDTO
from common.schemas.user import UserDTO as User
from game_client.bot.resources.fsm_states.states import BotState as GameState
from game_client.telegram_bot.base.base_orchestrator import BaseBotOrchestrator
from game_client.telegram_bot.base.view_dto import UnifiedViewDTO
from game_client.telegram_bot.features.scenario.client import ScenarioClient
from game_client.telegram_bot.features.scenario.resources.keyboards.scenario_callback import ScenarioCallback
from game_client.telegram_bot.features.scenario.system.scenario_ui_service import ScenarioUIService
from game_client.telegram_bot.services.error.logic.orchestrator import ErrorBotOrchestrator


class ScenarioBotOrchestrator(BaseBotOrchestrator):
    """
    Оркестратор UI для системы сценариев.
    Координирует получение данных от Core и их отрисовку через UI-сервис.
    Теперь содержит логику роутинга действий (Action Dispatching).
    """

    def __init__(self, client: ScenarioClient):
        super().__init__(expected_state=GameState.scenario)
        self._client = client
        self._ui_service = ScenarioUIService()
        self._error_orchestrator = ErrorBotOrchestrator()

    async def handle_request(self, user_id: int, callback_data: ScenarioCallback) -> Any:
        """
        Главная точка входа для обработки действий пользователя.
        Парсит callback_data и вызывает соответствующий метод бизнес-логики.
        """
        action = callback_data.action

        if action == "initialize":
            return await self._process_entry_point(user_id, str(callback_data.quest_key))

        elif action == "step":
            return await self._handle_step_action(user_id, str(callback_data.action_id))

        else:
            # Неизвестный экшен
            return self._error_orchestrator.view_generic_error(user_id, f"Unknown scenario action: {action}")

    async def _process_entry_point(self, user_id: int, quest_key: str | None = None) -> Any:
        """
        Внутренняя логика входа (initialize).
        """
        char_id = await self.director.get_char_id()
        if not char_id:
            return self._error_orchestrator.view_session_expired(user_id, "ScenarioEntry")

        if not quest_key:
            return self._error_orchestrator.view_generic_error(user_id, "Quest key required for initialization")

        response = await self._client.initialize(char_id, quest_key)

        if result := await self.check_and_switch_state(response):
            return result

        return await self.render(response.payload)

    async def _handle_step_action(self, user_id: int, action_id: str) -> Any:
        """
        Внутренняя логика шага (step).
        """
        char_id = await self.director.get_char_id()
        if not char_id:
            return self._error_orchestrator.view_session_expired(user_id, "ScenarioAction")

        response = await self._client.step(char_id, action_id)

        if result := await self.check_and_switch_state(response):
            return result

        return await self.render(response.payload)

    async def render(self, payload: Any) -> UnifiedViewDTO:
        """
        Превращает ScenarioPayloadDTO в UnifiedViewDTO.
        """
        if isinstance(payload, dict):
            with contextlib.suppress(Exception):
                payload = ScenarioPayloadDTO(**payload)

        if isinstance(payload, ScenarioPayloadDTO):
            view_result = self._ui_service.render_scene(payload)
            return UnifiedViewDTO(menu=None, content=view_result, clean_history=False)

        if isinstance(payload, User):
            # Ошибка: Лобби передало User вместо Payload
            return self._error_orchestrator.view_generic_error(
                payload.telegram_id, "Invalid payload: User object received"
            )

        if isinstance(payload, int):
            return self._error_orchestrator.view_generic_error(payload, "Invalid payload: int received")

        raise ValueError(f"Scenario render received invalid payload: {type(payload)}")
