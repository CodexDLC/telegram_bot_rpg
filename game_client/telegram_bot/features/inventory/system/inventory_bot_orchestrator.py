from typing import Any

from common.schemas.inventory.schemas import InventoryUIPayloadDTO
from game_client.telegram_bot.base.base_orchestrator import BaseBotOrchestrator
from game_client.telegram_bot.base.view_dto import UnifiedViewDTO, ViewResultDTO
from game_client.telegram_bot.features.inventory.client import InventoryClient
from game_client.telegram_bot.features.inventory.resources.keyboards.callbacks import InventoryActionCB, InventoryViewCB
from game_client.telegram_bot.features.inventory.system.inventory_ui_service import InventoryUIService


class InventoryBotOrchestrator(BaseBotOrchestrator):
    """
    Оркестратор клиентской части Инвентаря.
    Обрабатывает ответы от Gateway и вызывает UI Service.
    """

    def __init__(self, client: InventoryClient, expected_state: str | None = None):
        super().__init__(expected_state)
        self.client = client
        self.ui_service = InventoryUIService()

    async def render_content(self, payload: Any) -> ViewResultDTO:
        """
        Реализация абстрактного метода.
        Превращает payload (InventoryUIPayloadDTO) в ViewResultDTO.
        """
        # Валидация типа (Pydantic сам это сделает, если мы используем DTO, но здесь Any)
        if isinstance(payload, dict):
            dto = InventoryUIPayloadDTO(**payload)
        elif isinstance(payload, InventoryUIPayloadDTO):
            dto = payload
        else:
            raise ValueError(f"Invalid payload type: {type(payload)}")

        return self.ui_service.render(dto)

    async def handle_view_request(self, cb: InventoryViewCB) -> UnifiedViewDTO:
        """
        Обработка навигации (GET).
        """
        char_id = await self.director.get_char_id()
        if not char_id:
            # TODO: Handle error (redirect to login?)
            return UnifiedViewDTO(alert_text="Character not found")

        # Формируем параметры
        kwargs = {}
        if cb.section:
            kwargs["section"] = cb.section
        if cb.category:
            kwargs["category"] = cb.category
        if cb.page:
            kwargs["page"] = str(cb.page)  # Convert int to str for query params
        if cb.item_id:
            kwargs["item_id"] = str(cb.item_id)

        # Вызов API через клиент
        response = await self.client.get_view(char_id, cb.target, **kwargs)

        return await self.process_response(response)

    async def handle_action_request(self, cb: InventoryActionCB) -> UnifiedViewDTO:
        """
        Обработка действий (POST).
        """
        char_id = await self.director.get_char_id()
        if not char_id:
            return UnifiedViewDTO(alert_text="Character not found")

        kwargs = {"item_id": str(cb.item_id)}
        if cb.slot:
            kwargs["slot"] = cb.slot

        # Вызов API через клиент
        response = await self.client.handle_action(char_id, cb.action, **kwargs)

        return await self.process_response(response)
