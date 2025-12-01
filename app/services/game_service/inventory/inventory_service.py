# app/services/game_service/inventory/inventory_service.py
from typing import cast

from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from app.resources.schemas_dto.item_dto import InventoryItemDTO, ItemType
from app.services.game_service.matchmaking_service import MatchmakingService
from app.services.game_service.stats_aggregation_service import StatsAggregationService
from database.repositories import get_inventory_repo, get_wallet_repo
from database.repositories.ORM.wallet_repo import ResourceTypeGroup

BASE_INVENTORY_SIZE = 20


class InventoryService:
    """
    Сервис управления имуществом игрока.
    """

    def __init__(self, session: AsyncSession, char_id: int):
        self.session = session
        self.char_id = char_id
        self.inventory_repo = get_inventory_repo(session)
        self.wallet_repo = get_wallet_repo(session)

    # =========================================================================
    # 1. РЕСУРСЫ (Wallet)
    # =========================================================================

    async def add_resource(self, subtype: str, amount: int) -> int:
        group = self._map_subtype_to_group(subtype)

        new_total = await self.wallet_repo.add_resource(char_id=self.char_id, group=group, key=subtype, amount=amount)
        log.info(f"Wallet: +{amount} {subtype} (Total: {new_total})")
        return new_total

    async def get_dust_amount(self):
        return await self.wallet_repo.get_resource_amount(char_id=self.char_id, group="currency", key="dust")

    async def consume_resource(self, subtype: str, amount: int) -> bool:
        group = self._map_subtype_to_group(subtype)

        return await self.wallet_repo.remove_resource(char_id=self.char_id, group=group, key=subtype, amount=amount)

        # =========================================================================
        # 🛠 ЛОГИКА ВМЕСТИМОСТИ (Новое)
        # =========================================================================

    async def get_capacity(self) -> tuple[int, int]:
        """
        Возвращает (занято, всего).
        Считает бонус от статов (Perception) через Агрегатор.
        """
        # 1. Считаем занятые слоты (только то, что в сумке)
        all_items = await self.inventory_repo.get_all_items(self.char_id)
        in_bag = [i for i in all_items if i.location == "inventory"]
        current_slots = len(in_bag)

        # 2. Считаем Максимум через Агрегатор
        agg_service = StatsAggregationService(self.session)
        total_stats = await agg_service.get_character_total_stats(self.char_id)

        slots_bonus = 0
        # Безопасно достаем модификатор inventory_slots_bonus
        if total_stats and "modifiers" in total_stats:
            mod_data = total_stats["modifiers"].get("inventory_slots_bonus")
            if mod_data:
                slots_bonus = int(mod_data.get("total", 0))

        max_slots = BASE_INVENTORY_SIZE + slots_bonus

        return current_slots, max_slots

    async def has_free_slots(self, amount: int = 1) -> bool:
        """Проверяет, есть ли место для N предметов."""
        current, max_cap = await self.get_capacity()
        return (current + amount) <= max_cap

    # =========================================================================
    # 2. ПРЕДМЕТЫ (Inventory)
    # =========================================================================

    async def claim_item(self, item_id: int) -> bool:
        item = await self.inventory_repo.get_item_by_id(item_id)
        if not item:
            log.error(f"Ошибка: Предмет ID={item_id} не найден.")
            return False

        success = await self.inventory_repo.transfer_item(
            inventory_id=item_id, new_owner_id=self.char_id, new_location="inventory"
        )

        if success:
            log.info(f"Предмет {item_id} ({item.data.name}) получен игроком {self.char_id}.")
            return True
        return False

    async def equip_item(self, item_id: int) -> tuple[bool, str]:
        item = await self.inventory_repo.get_item_by_id(item_id)

        if not item or item.character_id != self.char_id:
            return False, "Предмет недоступен."

        if item.item_type not in (ItemType.WEAPON, ItemType.ARMOR, ItemType.ACCESSORY):
            return False, "Это нельзя надеть."

        await self._handle_slot_conflicts(item)

        if await self.inventory_repo.move_item(item_id, "equipped"):
            # 🔥 ХУК: Обновляем GS, так как статы изменились
            # Мы не ждем результат (fire and forget), чтобы UI не тормозил,
            # но в рамках одного request лучше подождать (await).
            mm_service = MatchmakingService(self.session)
            await mm_service.refresh_gear_score(self.char_id)

            return True, f"Надето: {item.data.name}"

        return False, "Ошибка БД."

    async def unequip_item(self, item_id: int) -> tuple[bool, str]:
        item = await self.inventory_repo.get_item_by_id(item_id)
        if not item or item.character_id != self.char_id:
            return False, "Ошибка."

        if await self.inventory_repo.move_item(item_id, "inventory"):
            # 🔥 ХУК
            mm_service = MatchmakingService(self.session)
            await mm_service.refresh_gear_score(self.char_id)

            return True, f"Снято: {item.data.name}"

        return False, "Ошибка БД."

    async def drop_item(self, item_id: int) -> bool:
        item = await self.inventory_repo.get_item_by_id(item_id)
        if not item or item.character_id != self.char_id:
            return False

        if item.location == "equipped":
            await self.inventory_repo.move_item(item_id, "inventory")

        return await self.inventory_repo.delete_item(item_id)

    # =========================================================================
    # ХЕЛПЕРЫ
    # =========================================================================

    async def get_items(self, location: str = "inventory") -> list[InventoryItemDTO]:
        """Возвращает только уникальные предметы."""
        return await self.inventory_repo.get_items_by_location(self.char_id, location)

    def _map_subtype_to_group(self, subtype: str) -> ResourceTypeGroup:
        """
        Определяет группу ресурсов для WalletRepo.
        """
        mapping = {
            "currency": ("dust", "shard", "core"),
            "ores": ("ore", "ingot", "stone"),
            "leathers": ("leather", "hide", "skin"),
            "fabrics": ("cloth", "fiber"),
            "organics": ("herb", "food", "meat"),
        }

        for group, keywords in mapping.items():
            if any(keyword in subtype for keyword in keywords):
                return cast(ResourceTypeGroup, group)

        return "parts"

    async def _handle_slot_conflicts(self, new_item: InventoryItemDTO) -> None:
        """Авто-снятие вещей при конфликте слотов."""
        if new_item.item_type not in (ItemType.WEAPON, ItemType.ARMOR, ItemType.ACCESSORY):
            return

        # FIX: Используем правильный код ошибки mypy [union-attr]
        required_slots = set(new_item.data.valid_slots)  # type: ignore[union-attr]

        equipped = await self.inventory_repo.get_items_by_location(self.char_id, "equipped")

        for old in equipped:
            if old.item_type not in (ItemType.WEAPON, ItemType.ARMOR, ItemType.ACCESSORY):
                continue

            # FIX: Используем правильный код ошибки mypy [union-attr]
            old_slots = set(old.data.valid_slots)  # type: ignore[union-attr]

            if not required_slots.isdisjoint(old_slots):
                await self.unequip_item(old.inventory_id)
