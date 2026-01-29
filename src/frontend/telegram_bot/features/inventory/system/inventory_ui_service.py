from src.frontend.telegram_bot.base.view_dto import ViewResultDTO
from src.frontend.telegram_bot.features.inventory.components.bag_ui import BagUI
from src.frontend.telegram_bot.features.inventory.components.details_ui import DetailsUI
from src.frontend.telegram_bot.features.inventory.components.doll_ui import DollUI
from src.shared.enums.inventory_enums import InventoryViewTarget
from src.shared.schemas.inventory import InventoryUIPayloadDTO


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
