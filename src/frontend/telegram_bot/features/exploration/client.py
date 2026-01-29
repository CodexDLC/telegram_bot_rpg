from typing import Any

from src.frontend.telegram_bot.core.api_client import BaseApiClient
from src.shared.schemas.response import CoreResponseDTO


class ExplorationClient(BaseApiClient):
    """
    HTTP клиент для взаимодействия с backend /exploration/...
    """

    async def move(
        self, char_id: int, direction: str | None = None, target_id: str | None = None
    ) -> CoreResponseDTO[Any]:
        """
        POST /exploration/move
        Перемещение персонажа.
        """
        body: dict[str, Any] = {"char_id": char_id}
        if target_id:
            body["target_id"] = target_id
        if direction:
            body["direction"] = direction

        data = await self._request("POST", "/exploration/move", json=body)
        return CoreResponseDTO[Any](**data)

    async def look_around(self, char_id: int) -> CoreResponseDTO[Any]:
        """
        GET /exploration/look_around
        Обзор локации.
        """
        data = await self._request("GET", "/exploration/look_around", params={"char_id": char_id})
        return CoreResponseDTO[Any](**data)

    async def interact(self, char_id: int, action: str, target_id: str | None = None) -> CoreResponseDTO[Any]:
        """
        POST /exploration/interact
        Взаимодействие.
        """
        body: dict[str, Any] = {"char_id": char_id, "action": action}
        if target_id:
            body["target_id"] = target_id

        data = await self._request("POST", "/exploration/interact", json=body)
        return CoreResponseDTO[Any](**data)
