from typing import Any

from common.schemas.game_menu import GameMenuDTO, MenuActionRequest
from common.schemas.response import CoreResponseDTO
from game_client.telegram_bot.core.api_client import BaseApiClient


class MenuClient(BaseApiClient):
    """
    Клиент для взаимодействия с Game Menu API.
    """

    async def get_menu_view(self, char_id: int) -> CoreResponseDTO[GameMenuDTO]:
        """
        Получает текущее состояние меню.
        """
        endpoint = "/api/v1/game-menu/view"
        params = {"char_id": char_id}

        response_data = await self._request("GET", endpoint, params=params)

        # Валидация ответа через Pydantic
        return CoreResponseDTO[GameMenuDTO].model_validate(response_data)

    async def dispatch_action(self, char_id: int, action_id: str) -> CoreResponseDTO[Any]:
        """
        Отправляет действие меню на бэкенд.
        """
        endpoint = "/api/v1/game-menu/dispatch"
        payload = MenuActionRequest(char_id=char_id, action_id=action_id).model_dump()

        response_data = await self._request("POST", endpoint, json=payload)

        return CoreResponseDTO[Any].model_validate(response_data)
