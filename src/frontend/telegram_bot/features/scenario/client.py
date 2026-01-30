from src.frontend.telegram_bot.core.api_client import BaseApiClient
from src.shared.schemas.response import CoreResponseDTO


class ScenarioClient(BaseApiClient):
    """
    HTTP клиент для Scenario API.
    Обертка над HTTP API /scenario/...
    """

    async def initialize(self, char_id: int, quest_key: str) -> CoreResponseDTO:
        """
        POST /scenario/initialize
        Запуск нового сценария.
        """
        body = {"quest_key": quest_key}

        data = await self._request("POST", "/scenario/initialize", params={"char_id": char_id}, json=body)
        return CoreResponseDTO(**data)

    async def step(self, char_id: int, action_id: str) -> CoreResponseDTO:
        """
        POST /scenario/step
        Выполнение шага.
        """
        data = await self._request("POST", "/scenario/step", params={"char_id": char_id, "action_id": action_id})
        return CoreResponseDTO(**data)
