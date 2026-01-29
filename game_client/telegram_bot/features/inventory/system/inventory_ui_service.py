from common.schemas.inventory.enums import InventoryViewTarget
from common.schemas.inventory.schemas import InventoryUIPayloadDTO
from game_client.telegram_bot.base.view_dto import ViewResultDTO
from game_client.telegram_bot.features.inventory.components.bag_ui import BagUI
from game_client.telegram_bot.features.inventory.components.details_ui import DetailsUI
from game_client.telegram_bot.features.inventory.components.doll_ui import DollUI


class InventoryUIService:
    """
    Фасад для UI инвентаря.
    Делегирует рендеринг специализированным компонентам в зависимости от экрана.
    """

    def __init__(self):
        self.doll_ui = DollUI()
        self.bag_ui = BagUI()
        self.details_ui = DetailsUI()

    def render(self, payload: InventoryUIPayloadDTO) -> ViewResultDTO:
        """
        Рендерит экран инвентаря.
        """
        if payload.screen == InventoryViewTarget.MAIN:
            return self.doll_ui.render(payload)
        elif payload.screen == InventoryViewTarget.BAG:
            return self.bag_ui.render(payload)
        elif payload.screen == InventoryViewTarget.DETAILS:
            return self.details_ui.render(payload)

        raise ValueError(f"Unknown screen: {payload.screen}")
