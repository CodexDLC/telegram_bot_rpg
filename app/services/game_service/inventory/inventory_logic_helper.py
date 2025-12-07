# app/services/game_service/inventory/inventory_logic_helper.py
from typing import cast

from loguru import logger as log

from app.resources.schemas_dto.item_dto import EquippedSlot, InventoryItemDTO, ItemType
from database.db_contract.i_inventory_repo import IInventoryRepo
from database.repositories.ORM.wallet_repo import ResourceTypeGroup

# Логика конфликтов остается здесь
CONFLICT_MAP: dict[EquippedSlot, list[EquippedSlot]] = {
    EquippedSlot.TWO_HAND: [EquippedSlot.MAIN_HAND, EquippedSlot.OFF_HAND],
    EquippedSlot.MAIN_HAND: [EquippedSlot.TWO_HAND],
}


class InventoryLogicHelpers:
    """
    Класс-помощник, содержащий внутреннюю логику и чистые функции для InventoryService (Layer 3).
    """

    def __init__(self, inventory_repo: IInventoryRepo):
        self.inventory_repo = inventory_repo
        log.debug("InventoryLogicHelpers | status=initialized")

    @staticmethod
    def map_subtype_to_group(subtype: str) -> ResourceTypeGroup:
        """
        [STATIC] Определяет группу ресурсов для WalletRepo на основе подтипа.
        """
        mapping = {
            "currency": ("dust", "shard", "core"),
            "ores": ("ore", "ingot", "stone"),
            "leathers": ("leather", "hide", "skin", "scale"),
            "fabrics": ("cloth", "fiber", "weave", "roll", "rag"),
            "organics": ("herb", "food", "meat"),
        }

        for group, keywords in mapping.items():
            if any(keyword in subtype for keyword in keywords):
                return cast(ResourceTypeGroup, group)

        return "parts"

    async def get_equipped_map(self, char_id: int) -> dict[EquippedSlot, InventoryItemDTO]:
        equipped_items = await self.inventory_repo.get_items_by_location(char_id, "equipped")
        equipped_map = {EquippedSlot(item.equipped_slot): item for item in equipped_items if item.equipped_slot}
        return equipped_map

    async def handle_slot_conflicts(self, new_item: InventoryItemDTO, target_slot: EquippedSlot) -> None:
        equipped_map = await self.get_equipped_map(new_item.character_id)
        items_to_unequip: list[InventoryItemDTO] = []

        if target_slot in equipped_map:
            items_to_unequip.append(equipped_map[target_slot])

        slots_to_check = CONFLICT_MAP.get(target_slot, [])
        for conflict_slot in slots_to_check:
            if conflict_slot in equipped_map:
                items_to_unequip.append(equipped_map[conflict_slot])

        for old_item in set(items_to_unequip):
            if old_item.item_type in (ItemType.RESOURCE, ItemType.CURRENCY):
                continue
            else:
                await self.inventory_repo.update_fields(
                    old_item.inventory_id, {"location": "inventory", "equipped_slot": None, "quick_slot_position": None}
                )
                log.info(f"Конфликт разрешен: снят {old_item.data.name} из {old_item.equipped_slot}.")

    async def get_quick_slot_limit(self, char_id: int) -> int:
        equipped_map = await self.get_equipped_map(char_id)
        belt_item = equipped_map.get(EquippedSlot.BELT_ACCESSORY)

        base_quick_slot_limit = 0
        if not belt_item or belt_item.item_type in (ItemType.RESOURCE, ItemType.CURRENCY):
            return base_quick_slot_limit
        else:
            current_limit = 0
            if belt_item.data.bonuses:
                capacity = belt_item.data.bonuses.get("quick_slot_capacity", 0)
                if isinstance(capacity, (int, float)):
                    current_limit = int(capacity)

            final_limit = max(base_quick_slot_limit, current_limit)
            return final_limit

    async def unbind_quick_slot(self, item_id: int, char_id: int) -> tuple[bool, str]:
        item = await self.inventory_repo.get_item_by_id(item_id)

        if not item or item.character_id != char_id:
            return False, "Предмет не найден или не принадлежит вам."

        if not item.quick_slot_position:
            return False, "Предмет не находится в быстром слоте."

        success = await self.inventory_repo.update_fields(item_id, {"quick_slot_position": None})

        if success:
            log.info(f"QuickSlot | action=unbind item_id={item_id} char_id={char_id}")
            return True, "Предмет убран из слота быстрого доступа."
        return False, "Ошибка базы данных."

    async def get_filtered_items(
        self, items: list[InventoryItemDTO], section: str, category: str
    ) -> list[InventoryItemDTO]:
        """
        Фильтрует предметы для отображения в инвентаре (Frontend API).
        Поддерживает фильтрацию по секциям, типам предметов, группам ресурсов и конкретным слотам.
        """
        filtered = []

        for item in items:
            # 1. Фильтрация по Секции (Локация предмета)
            # Если мы смотрим "Инвентарь", нам не нужны надетые вещи (они на кукле)
            if (
                section == "inventory"
                and item.location != "inventory"
                or section == "equip"
                and item.location != "inventory"
            ):
                continue

                # 2. Фильтрация по Категории (Тип фильтра)
            if category == "all":
                filtered.append(item)
                continue

            # А. Ресурсы: Проверяем принадлежность к группе (руды, ткани и т.д.)
            if section == "resource":
                # item.subtype -> Group (e.g. iron_ore -> ores)
                item_group = self.map_subtype_to_group(item.subtype)
                if item_group == category:
                    filtered.append(item)
                continue

            # Б. Экипировка: Фильтр по Слоту (если category == 'head_armor' и т.д.)
            # Проверяем, есть ли у предмета список валидных слотов и входит ли туда наш слот
            if (
                hasattr(item.data, "valid_slots")
                and item.data.valid_slots
                and any(str(s) == category for s in item.data.valid_slots)
            ):
                filtered.append(item)
                continue

            # В. Экипировка: Фильтр по Типу (weapon, armor, accessory) - для табов
            if item.item_type.value == category:
                filtered.append(item)
                continue

            # Г. Запасной вариант: совпадение по подтипу (на всякий случай)
            if item.subtype == category:
                filtered.append(item)

        return filtered
