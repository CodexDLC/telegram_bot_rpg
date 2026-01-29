from typing import Any

from src.frontend.telegram_bot.core.api_client import BaseApiClient
from src.shared.schemas.response import CoreResponseDTO


class ArenaClient(BaseApiClient):
    async def action(
        self, char_id: int, action: str, mode: str | None = None, value: Any | None = None
    ) -> CoreResponseDTO:
        """
        Отправляет действие на backend.
        """
        payload = {"action": action, "mode": mode, "value": value}
        # Используем _request, так как post не определен в BaseApiClient
        data = await self._request("POST", f"arena/{char_id}/action", json=payload)
        return CoreResponseDTO(**data)
