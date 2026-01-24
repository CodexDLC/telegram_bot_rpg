# app/services/ui_service/inventory/inventory_ui_service.py
from typing import Any

from loguru import logger as log

from apps.common.schemas_dto import InventoryItemDTO
from game_client.bot.resources.texts.ui_messages import DEFAULT_ACTOR_NAME
from game_client.bot.ui_service.base_service import BaseUIService
from game_client.bot.ui_service.helpers_ui.dto.ui_common_dto import ViewResultDTO

from .inventory_details_ui import InventoryDetailsUI
from .inventory_list_ui import InventoryListUI
from .inventory_main_menu_ui import InventoryMainMenuUI
from .inventory_quick_slot_ui import InventoryQuickSlotUI


class InventoryUIService(BaseUIService):
    """
    Фасад UI-слоя для Инвентаря.
    """

    def __init__(
        self,
        char_id: int,
        user_id: int,
        state_data: dict[str, Any],
    ):
        super().__init__(char_id=char_id, state_data=state_data)
        self.user_id = user_id
        # Используем дефолтное имя, так как в BaseUIService его больше нет
        self.actor_name = DEFAULT_ACTOR_NAME

        # Инициализация специализированных UI-помощников
        self._main_menu_ui = InventoryMainMenuUI(
            char_id=self.char_id,
            user_id=self.user_id,
            state_data=self.state_data,
        )
        self._list_ui = InventoryListUI(
            char_id=self.char_id,
            user_id=self.user_id,
            state_data=self.state_data,
        )
        self._details_ui = InventoryDetailsUI(
            char_id=self.char_id,
            user_id=self.user_id,
            state_data=self.state_data,
        )
        self._quick_slot_ui = InventoryQuickSlotUI(
            char_id=self.char_id,
            user_id=self.user_id,
            state_data=self.state_data,
        )

        log.debug(f"InventoryUIService (Facade) | status=initialized char_id={char_id}")

    def render_main_menu(self, summary: dict, equipped: list[InventoryItemDTO]) -> ViewResultDTO:
        """Уровень 0: Делегирует рендеринг главному меню."""
        return self._main_menu_ui.render(summary, equipped)

    def render_item_list(
        self,
        items_on_page: list[InventoryItemDTO],
        total_pages: int,
        current_page: int,
        section: str,
        category: str,
        filter_type: str = "category",
    ) -> ViewResultDTO:
        """Уровень 1: Делегирует рендеринг спискам."""
        return self._list_ui.render(items_on_page, total_pages, current_page, section, category, filter_type)

    def render_item_details(
        self,
        item: InventoryItemDTO,
        comparison_data: dict | None,
        category: str,
        page: int,
        filter_type: str,
    ) -> ViewResultDTO:
        """Уровень 2: Делегирует рендеринг детальной карточке."""
        return self._details_ui.render(item, comparison_data, category, page, filter_type)

    def render_belt_overview(self, max_slots: int, items_in_bag: list[InventoryItemDTO]) -> ViewResultDTO:
        """Рендерит меню слотов пояса."""
        return self._quick_slot_ui.render_belt_overview(max_slots, items_in_bag)

    def render_quick_slot_selection_menu(
        self, item_name: str, item_id: int, max_slots: int, context_data: dict
    ) -> ViewResultDTO:
        """Уровень 3: Делегирует рендеринг меню выбора слота."""
        return self._quick_slot_ui.render_quick_slot_selection_menu(item_name, item_id, max_slots, context_data)
