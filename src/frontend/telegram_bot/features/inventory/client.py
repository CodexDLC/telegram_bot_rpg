from src.frontend.telegram_bot.core.api_client import BaseApiClient
from src.shared.schemas.response import CoreCompositeResponseDTO


class InventoryClient(BaseApiClient):
    """
    HTTP клиент для взаимодействия с backend /inventory/...
    """

    async def get_view(self, char_id: int, target: str, **kwargs) -> CoreCompositeResponseDTO:
        """
        GET /inventory/{char_id}/{target}
        Получает данные для отрисовки экрана (main, bag, details).
        """
        # Формируем query params из kwargs
        params = {k: v for k, v in kwargs.items() if v is not None}

        data = await self._request("GET", f"/inventory/{char_id}/{target}", params=params)
        return CoreCompositeResponseDTO(**data)

    async def handle_action(self, char_id: int, action: str, **kwargs) -> CoreCompositeResponseDTO:
        """
        POST /inventory/{char_id}/{action}
        Выполняет действие (equip, unequip, use, move).
        """
        # Формируем body из kwargs
        body = {k: v for k, v in kwargs.items() if v is not None}

        data = await self._request("POST", f"/inventory/{char_id}/{action}", json=body)
        return CoreCompositeResponseDTO(**data)
