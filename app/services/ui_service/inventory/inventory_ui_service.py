# app/services/ui_service/inventory/inventory_ui_service.py
from typing import Any

from aiogram.types import InlineKeyboardMarkup
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.core_service.manager.account_manager import AccountManager
from app.services.game_service.inventory.inventory_service import InventoryService
from app.services.ui_service.base_service import BaseUIService

from .inventory_details_ui import InventoryDetailsUI
from .inventory_list_ui import InventoryListUI
from .inventory_main_menu_ui import InventoryMainMenuUI
from .inventory_quick_slot_ui import InventoryQuickSlotUI


class InventoryUIService(BaseUIService):
    """
    Фасад UI-слоя для Инвентаря.

    Этот класс является чистым оркестратором (Layer 2 Facade).
    Он инициализирует Layer 3 (InventoryService) и делегирует
    всю логику рендеринга и действий специализированным UI-помощникам.
    """

    # Размер страницы, унаследованный от InventoryListUI
    PAGE_SIZE = 9

    def __init__(
        self,
        char_id: int,
        user_id: int,
        session: AsyncSession,
        state_data: dict[str, Any],
        account_manager: AccountManager,
    ):
        super().__init__(char_id=char_id, state_data=state_data)
        # user_id передается напрямую для генерации кнопок (security)
        self.user_id = user_id
        self.session = session

        # 1. 🔥 Инициализация Layer 3 (Game Service)
        self.inventory_service = InventoryService(
            session=self.session, char_id=self.char_id, account_manager=account_manager
        )

        # 2. 🔥 Инициализация специализированных UI-помощников
        self._main_menu_ui = InventoryMainMenuUI(
            char_id=self.char_id,
            user_id=self.user_id,
            state_data=self.state_data,
            inventory_service=self.inventory_service,
        )
        self._list_ui = InventoryListUI(
            char_id=self.char_id,
            user_id=self.user_id,
            state_data=self.state_data,
            inventory_service=self.inventory_service,
        )
        self._details_ui = InventoryDetailsUI(
            char_id=self.char_id,
            user_id=self.user_id,
            state_data=self.state_data,
            inventory_service=self.inventory_service,
        )
        self._quick_slot_ui = InventoryQuickSlotUI(
            char_id=self.char_id,
            user_id=self.user_id,
            state_data=self.state_data,
            inventory_service=self.inventory_service,
        )

        log.debug(f"InventoryUIService (Facade) | status=initialized char_id={char_id}")

    # =========================================================================
    # ДЕЛЕГАТЫ РЕНДЕРИНГА (VIEWS)
    # =========================================================================

    async def render_main_menu(self) -> tuple[str, InlineKeyboardMarkup]:
        """Уровень 0: Делегирует рендеринг главному меню."""
        return await self._main_menu_ui.render()

    async def render_item_list(
        self, section: str, category: str, page: int = 0, filter_type: str = "category"
    ) -> tuple[str, InlineKeyboardMarkup]:
        """Уровень 1: Делегирует рендеринг спискам."""
        return await self._list_ui.render(section, category, page, filter_type)

    async def render_item_details(
        self, item_id: int, category: str, page: int, filter_type: str
    ) -> tuple[str, InlineKeyboardMarkup]:
        """Уровень 2: Делегирует рендеринг детальной карточке."""
        return await self._details_ui.render(item_id, category, page, filter_type)

    async def render_quick_slot_selection_menu(
        self, item_id: int, context_data: dict
    ) -> tuple[str, InlineKeyboardMarkup]:
        """Уровень 3: Делегирует рендеринг меню выбора слота."""
        return await self._quick_slot_ui.render_quick_slot_selection_menu(item_id, context_data)

    async def render_belt_overview(self) -> tuple[str, InlineKeyboardMarkup]:
        """Рендерит меню слотов пояса."""
        return await self._quick_slot_ui.render_belt_overview()

    # =========================================================================
    # ДЕЛЕГАТЫ ДЕЙСТВИЙ (ACTIONS)
    # =========================================================================

    async def action_bind_quick_slot(self, item_id: int, quick_slot_key: str) -> tuple[bool, str]:
        """Делегирует действие привязки слота."""
        # Layer 2 вызывает Layer 3 через помощника
        return await self._quick_slot_ui.action_bind(item_id, quick_slot_key)

    async def action_unbind_quick_slot(self, item_id: int) -> tuple[bool, str]:
        """Делегирует действие отвязки слота."""
        # Layer 2 вызывает Layer 3 через помощника
        return await self._quick_slot_ui.action_unbind(item_id)
