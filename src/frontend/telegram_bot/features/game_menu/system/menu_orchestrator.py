from typing import Any

from src.frontend.telegram_bot.base.base_orchestrator import BaseBotOrchestrator
from src.frontend.telegram_bot.base.view_dto import UnifiedViewDTO, ViewResultDTO
from src.frontend.telegram_bot.features.game_menu.client import MenuClient
from src.frontend.telegram_bot.features.game_menu.resources.keyboards.menu_callback import MenuCallback
from src.frontend.telegram_bot.features.game_menu.system.menu_ui_service import MenuUIService
from src.shared.schemas.game_menu import GameMenuDTO


class MenuBotOrchestrator(BaseBotOrchestrator):
    """
    Оркестратор для Game Menu.
    """

    def __init__(self, client: MenuClient, ui_service: MenuUIService):
        super().__init__(expected_state=None)  # Меню доступно везде
        self.client = client
        self.ui_service = ui_service

    async def render_content(self, payload: Any) -> ViewResultDTO:
        """
        Рендерит меню из payload.
        """
        if isinstance(payload, dict):
            dto = GameMenuDTO(**payload)
        elif isinstance(payload, GameMenuDTO):
            dto = payload
        else:
            raise ValueError(f"Invalid payload type: {type(payload)}")

        return self.ui_service.render(dto)

    async def handle_request(self, char_id: int, cb: MenuCallback) -> UnifiedViewDTO:
        """
        Обрабатывает нажатие кнопки меню.
        """
        response = await self.client.dispatch_action(char_id, cb.action)
        return await self.process_response(response)
