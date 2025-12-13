from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.database.repositories import get_inventory_repo, get_wallet_repo
from apps.common.schemas_dto import EquippedSlot, InventoryItemDTO, ItemType, QuickSlot
from apps.common.services.core_service.manager.account_manager import AccountManager
from apps.game_core.game_service.matchmaking_service import MatchmakingService
from apps.game_core.game_service.stats_aggregation_service import StatsAggregationService

from .inventory_logic_helper import InventoryLogicHelpers

BASE_INVENTORY_SIZE = 20


class InventoryService:
    """
    Сервис для управления инвентарем и ресурсами игрока.
    """

    def __init__(self, session: AsyncSession, char_id: int, account_manager: AccountManager):
        self.session = session
        self.char_id = char_id
        self.account_manager = account_manager
        self.inventory_repo = get_inventory_repo(session)
        self.wallet_repo = get_wallet_repo(session)
        self.mm_service = MatchmakingService(session, self.account_manager)
        self.agg_service = StatsAggregationService(session)
        self.logic_helpers = InventoryLogicHelpers(inventory_repo=self.inventory_repo)
        log.debug(f"InventoryService | status=initialized char_id={char_id}")

    async def get_item_by_id(self, item_id: int) -> InventoryItemDTO | None:
        return await self.inventory_repo.get_item_by_id(item_id)

    async def get_items(self, location: str = "inventory") -> list[InventoryItemDTO]:
        """Возвращает список предметов персонажа, находящихся в указанной локации."""
        return await self.inventory_repo.get_items_by_location(self.char_id, location)

    async def get_filtered_items(
        self, items: list[InventoryItemDTO], section: str, category: str | None = None
    ) -> list[InventoryItemDTO]:
        """Алиас для обратной совместимости с UI."""
        return await self.logic_helpers.filter_and_sort_items(items=items, section=section, category=category)

    async def unbind_quick_slot(self, item_id: int) -> tuple[bool, str]:
        return await self.logic_helpers.unbind_quick_slot(item_id=item_id, char_id=self.char_id)

    async def get_quick_slot_limit(self) -> int:
        return await self.logic_helpers.get_quick_slot_limit(char_id=self.char_id)

    async def add_resource(self, subtype: str, amount: int) -> None:
        group = self.logic_helpers.get_resource_group(subtype)
        await self.wallet_repo.add_resource(char_id=self.char_id, group=group, key=subtype, amount=amount)
        log.info(f"InventoryService | action=add_resource char_id={self.char_id} subtype='{subtype}' amount={amount}")

    async def get_dust_amount(self) -> int:
        amount = await self.wallet_repo.get_resource_amount(char_id=self.char_id, group="currency", key="currency_dust")
        log.debug(f"InventoryService | action=get_dust_amount char_id={self.char_id} amount={amount}")
        return amount

    async def consume_resource(self, subtype: str, amount: int) -> bool:
        group = self.logic_helpers.get_resource_group(subtype)
        success = await self.wallet_repo.remove_resource(char_id=self.char_id, group=group, key=subtype, amount=amount)
        log.info(
            f"InventoryService | action=consume_resource char_id={self.char_id} subtype='{subtype}' amount={amount} success={success}"
        )
        return success

    async def get_capacity(self) -> tuple[int, int]:
        all_items = await self.inventory_repo.get_all_items(self.char_id)
        in_bag = [i for i in all_items if i.location == "inventory"]
        current_slots = len(in_bag)

        total_stats = await self.agg_service.get_character_total_stats(self.char_id)
        slots_bonus = 0
        if total_stats and "modifiers" in total_stats:
            mod_data = total_stats["modifiers"].get("inventory_slots_bonus")
            if mod_data:
                slots_bonus = int(mod_data.get("total", 0))

        max_slots = BASE_INVENTORY_SIZE + slots_bonus
        return current_slots, max_slots

    async def has_free_slots(self, amount: int = 1) -> bool:
        current, max_cap = await self.get_capacity()
        return (current + amount) <= max_cap

    async def equip_item(self, item_id: int, target_slot: EquippedSlot) -> tuple[bool, str]:
        item_to_equip = await self.inventory_repo.get_item_by_id(item_id)
        if not item_to_equip or item_to_equip.character_id != self.char_id:
            return False, "Предмет недоступен."

        if item_to_equip.item_type not in (ItemType.WEAPON, ItemType.ARMOR, ItemType.ACCESSORY):
            return False, "Это нельзя надеть."

        await self._handle_slot_conflicts(item_to_equip, target_slot)

        update_data = {"location": "equipped", "equipped_slot": target_slot.value, "quick_slot_position": None}
        if await self.inventory_repo.update_fields(item_id, update_data):
            await self.mm_service.refresh_gear_score(self.char_id)
            return True, f"Надето: {item_to_equip.data.name} в {target_slot.name}"
        return False, "Ошибка БД."

    async def _handle_slot_conflicts(self, item_to_equip: InventoryItemDTO, target_slot: EquippedSlot):
        equipped_items = await self.inventory_repo.get_equipped_items(self.char_id)
        items_to_unequip = []

        if target_slot in [EquippedSlot.MAIN_HAND, EquippedSlot.OFF_HAND, EquippedSlot.TWO_HAND]:
            if target_slot == EquippedSlot.TWO_HAND:
                items_to_unequip.extend(
                    [i for i in equipped_items if i.equipped_slot in [EquippedSlot.MAIN_HAND, EquippedSlot.OFF_HAND]]
                )
            else:
                items_to_unequip.extend([i for i in equipped_items if i.equipped_slot == EquippedSlot.TWO_HAND])

        items_to_unequip.extend([i for i in equipped_items if i.equipped_slot == target_slot])

        for item in items_to_unequip:
            await self.inventory_repo.move_item(item.inventory_id, "inventory")

    async def unequip_item(self, item_id: int) -> tuple[bool, str]:
        item = await self.inventory_repo.get_item_by_id(item_id)
        if not item or item.character_id != self.char_id:
            return False, "Ошибка."

        if await self.inventory_repo.move_item(item_id, "inventory"):
            await self.mm_service.refresh_gear_score(self.char_id)
            return True, f"Снято: {item.data.name}"
        return False, "Ошибка БД."

    async def move_to_quick_slot(self, item_id: int, position: QuickSlot) -> tuple[bool, str]:
        item = await self.inventory_repo.get_item_by_id(item_id)
        if not item or item.character_id != self.char_id:
            return False, "Предмет недоступен."

        if item.item_type != ItemType.CONSUMABLE or not item.data.is_quick_slot_compatible:
            return False, "Этот предмет нельзя поместить в быстрый слот."

        max_limit = await self.get_quick_slot_limit()
        target_pos_int = int(position.value.split("_")[-1])
        if target_pos_int > max_limit:
            return False, f"Слот недоступен. Лимит: {max_limit}."

        items = await self.inventory_repo.get_all_items(self.char_id)
        for existing_item in items:
            if existing_item.quick_slot_position == position.value and existing_item.inventory_id != item_id:
                await self.inventory_repo.update_fields(existing_item.inventory_id, {"quick_slot_position": None})
                break

        update_data = {"quick_slot_position": position.value}
        if await self.inventory_repo.update_fields(item_id, update_data):
            return True, f"Предмет {item.data.name} закреплен за {position.name}."
        return False, "Ошибка БД."
