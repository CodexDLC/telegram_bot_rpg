from typing import Any

from aiogram.types import User
from apps.common.schemas_dto.game_state_enum import GameState

from apps.common.schemas_dto.scenario_dto import ScenarioPayloadDTO
from game_client.bot.core_client.scenario_client import ScenarioClient
from game_client.bot.ui_service.base_bot_orchestrator import BaseBotOrchestrator
from game_client.bot.ui_service.dto.view_dto import UnifiedViewDTO
from game_client.bot.ui_service.error.error_bot_orchestrator import ErrorBotOrchestrator
from game_client.bot.ui_service.scenario.scenario_ui_service import ScenarioUIService


class ScenarioBotOrchestrator(BaseBotOrchestrator):
    """
    Оркестратор UI для системы сценариев.
    Координирует получение данных от Core и их отрисовку через UI-сервис.
    """

    def __init__(self, client: ScenarioClient):
        super().__init__(expected_state=GameState.SCENARIO)
        self._client = client
        self._ui_service = ScenarioUIService()
        self._error_orchestrator = ErrorBotOrchestrator()

    async def process_entry_point(self, user: User, quest_key: str | None = None) -> Any:
        """
        Точка входа в сценарий.
        """
        # Получаем char_id из сессии через Директора
        char_id = await self.director.get_char_id()
        if not char_id:
            return self._error_orchestrator.view_session_expired(user.id, "ScenarioEntry")

        if quest_key:
            response = await self._client.initialize_scenario(char_id, quest_key)
        else:
            response = await self._client.resume_scenario(char_id)

        if result := await self.check_and_switch_state(response):
            return result

        return await self.render(response.payload)

    async def handle_action(self, user: User, action_id: str) -> Any:
        """
        Обработка выбора игрока.
        """
        char_id = await self.director.get_char_id()
        if not char_id:
            return self._error_orchestrator.view_session_expired(user.id, "ScenarioAction")

        response = await self._client.step_scenario(char_id, action_id)

        if result := await self.check_and_switch_state(response):
            return result

        return await self.render(response.payload)

    async def render(self, payload: Any) -> UnifiedViewDTO:
        """
        Превращает ScenarioPayloadDTO в UnifiedViewDTO.
        """
        if isinstance(payload, ScenarioPayloadDTO):
            view_result = self._ui_service.render_scene(payload)
            return UnifiedViewDTO(menu=None, content=view_result, clean_history=False)

        if isinstance(payload, User):
            # Пытаемся восстановить сессию
            return await self.process_entry_point(payload)

        # Если пришел неизвестный тип payload, возвращаем ошибку
        # (но нам нужен user_id для генерации ошибки, а в render(payload) его может не быть)
        # В этом случае кидаем исключение, так как это баг разработки, а не рантайм юзера
        raise ValueError(f"Scenario render received invalid payload: {type(payload)}")
