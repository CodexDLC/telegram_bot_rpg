from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.schemas_dto import InventoryItemDTO, ItemType, QuickSlot
from apps.common.services.core_service.manager.account_manager import AccountManager
from apps.game_core.game_service.inventory.inventory_service import InventoryService


class InventoryCoreOrchestrator:
    """
    Оркестратор инвентаря (Core Layer).
    Единая точка входа для всех операций с инвентарем.
    """

    def __init__(self, session: AsyncSession, account_manager: AccountManager):
        self.session = session
        self.account_manager = account_manager

    def _get_service(self, char_id: int) -> InventoryService:
        return InventoryService(self.session, char_id, self.account_manager)

    async def get_inventory_summary(self, char_id: int) -> dict:
        """Возвращает сводку по инвентарю (вес, слоты, валюта)."""
        service = self._get_service(char_id)

        balance = await service.get_wallet_balance()
        weight = await service.calculate_total_weight()
        max_weight = await service.get_max_weight()

        return {"balance": balance, "weight": weight, "max_weight": max_weight}

    async def get_items(self, char_id: int, section: str, category: str, page: int, page_size: int) -> dict:
        """Возвращает список предметов с пагинацией."""
        service = self._get_service(char_id)

        all_items = await service.get_items("inventory")
        filtered_items = await service.get_filtered_items(all_items, section, category)

        total_items = len(filtered_items)
        total_pages = (total_items + page_size - 1) // page_size
        if total_pages == 0:
            total_pages = 1

        # Коррекция страницы
        if page >= total_pages:
            page = total_pages - 1
        if page < 0:
            page = 0

        start_idx = page * page_size
        end_idx = start_idx + page_size
        items_on_page = filtered_items[start_idx:end_idx]

        return {"items": items_on_page, "total_pages": total_pages, "current_page": page}

    async def get_item_details(self, char_id: int, item_id: int) -> InventoryItemDTO | None:
        """Возвращает детали предмета."""
        service = self._get_service(char_id)
        return await service.get_item_by_id(item_id)

    async def get_comparison(self, char_id: int, item: InventoryItemDTO) -> dict | None:
        """Возвращает данные для сравнения с надетым предметом."""
        if item.item_type in (ItemType.RESOURCE, ItemType.CURRENCY):
            return None

        target_slots = getattr(item.data, "valid_slots", [])
        if not target_slots:
            return None

        service = self._get_service(char_id)
        equipped_items = await service.get_items("equipped")

        old_item = None
        for eq in equipped_items:
            if eq.item_type in (ItemType.RESOURCE, ItemType.CURRENCY):
                continue
            eq_slots = getattr(eq.data, "valid_slots", [])
            if set(target_slots).intersection(set(eq_slots)):
                old_item = eq
                break

        if not old_item:
            return {"is_empty": True}

        new_bonuses = item.data.bonuses or {}
        old_bonuses = old_item.data.bonuses or {}
        all_bonuses = set(new_bonuses.keys()) | set(old_bonuses.keys())

        diffs = {}
        for stat in all_bonuses:
            new_val = new_bonuses.get(stat, 0)
            old_val = old_bonuses.get(stat, 0)
            diff = new_val - old_val
            if diff != 0:
                diffs[stat] = diff

        return {"is_empty": False, "old_item_name": old_item.data.name, "diffs": diffs}

    async def equip_item(self, char_id: int, item_id: int, slot: str) -> tuple[bool, str]:
        """Экипировка предмета."""
        # TODO: Реализовать логику экипировки.
        # 1. Получить предмет через service.get_item_by_id
        # 2. Определить слот (если slot="auto", взять из item.data.valid_slots)
        # 3. Вызвать service.equip_item(item_id, target_slot)
        return (True, "Equipped (STUB)")

    async def use_item(self, char_id: int, item_id: int) -> tuple[bool, str]:
        """Использование предмета."""
        service = self._get_service(char_id)
        return await service.use_item(item_id)

    async def get_quick_slot_limit(self, char_id: int) -> int:
        """Возвращает лимит быстрых слотов."""
        service = self._get_service(char_id)
        return await service.get_quick_slot_limit()

    async def bind_quick_slot(self, char_id: int, item_id: int, slot_key: str) -> tuple[bool, str]:
        """Привязывает предмет к слоту."""
        service = self._get_service(char_id)
        try:
            slot_enum = QuickSlot(slot_key)
            return await service.move_to_quick_slot(item_id, slot_enum)
        except ValueError:
            return False, "Неверный слот."

    async def unbind_quick_slot(self, char_id: int, item_id: int) -> tuple[bool, str]:
        """Отвязывает предмет от слота."""
        service = self._get_service(char_id)
        return await service.unbind_quick_slot(item_id)
