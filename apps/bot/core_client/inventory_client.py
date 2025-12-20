from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.schemas_dto import InventoryItemDTO
from apps.common.services.core_service.manager.account_manager import AccountManager
from apps.game_core.game_service.inventory.inventory_orchestrator import InventoryCoreOrchestrator


class InventoryClient:
    """
    Клиент для взаимодействия с системой инвентаря.
    """

    def __init__(self, session: AsyncSession, account_manager: AccountManager):
        self._orchestrator = InventoryCoreOrchestrator(session, account_manager)

    async def get_summary(self, char_id: int) -> dict:
        return await self._orchestrator.get_inventory_summary(char_id)

    async def get_items(self, char_id: int, section: str, category: str, page: int, page_size: int) -> dict:
        return await self._orchestrator.get_items(char_id, section, category, page, page_size)

    async def get_item_details(self, char_id: int, item_id: int) -> InventoryItemDTO | None:
        return await self._orchestrator.get_item_details(char_id, item_id)

    async def get_comparison(self, char_id: int, item: InventoryItemDTO) -> dict | None:
        return await self._orchestrator.get_comparison(char_id, item)

    async def equip_item(self, char_id: int, item_id: int, slot: str) -> tuple[bool, str]:
        return await self._orchestrator.equip_item(char_id, item_id, slot)

    async def use_item(self, char_id: int, item_id: int) -> tuple[bool, str]:
        return await self._orchestrator.use_item(char_id, item_id)

    async def get_quick_slot_limit(self, char_id: int) -> int:
        return await self._orchestrator.get_quick_slot_limit(char_id)

    async def bind_quick_slot(self, char_id: int, item_id: int, slot_key: str) -> tuple[bool, str]:
        return await self._orchestrator.bind_quick_slot(char_id, item_id, slot_key)

    async def unbind_quick_slot(self, char_id: int, item_id: int) -> tuple[bool, str]:
        return await self._orchestrator.unbind_quick_slot(char_id, item_id)
