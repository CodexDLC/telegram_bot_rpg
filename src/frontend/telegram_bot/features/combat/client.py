from typing import Any

from src.frontend.telegram_bot.core.api_client import BaseApiClient
from src.shared.schemas.response import CoreResponseDTO


class CombatClient(BaseApiClient):
    """
    Клиент боевой системы.
    Обертка над HTTP API /combat/...
    """

    async def get_view(self, char_id: int, view_type: str, params: dict[str, Any] = None) -> CoreResponseDTO:
        """
        GET /combat/{char_id}/view
        """
        params = params or {}
        params["view_type"] = view_type

        data = await self._request("GET", f"/combat/{char_id}/view", params=params)
        return CoreResponseDTO(**data)

    async def handle_action(self, char_id: int, action_type: str, payload: dict[str, Any]) -> CoreResponseDTO:
        """
        POST /combat/{char_id}/action
        """
        body = {"action_type": action_type, "payload": payload}

        data = await self._request("POST", f"/combat/{char_id}/action", json=body)
        return CoreResponseDTO(**data)
