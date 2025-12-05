# app/services/game_service/inventory/inventory_logic_helper.py
from typing import cast

from loguru import logger as log

from app.resources.schemas_dto.item_dto import EquippedSlot, InventoryItemDTO, ItemType
from database.db_contract.i_inventory_repo import IInventoryRepo
from database.repositories.ORM.wallet_repo import ResourceTypeGroup

# Логика конфликтов остается здесь, так как это часть логического домена
CONFLICT_MAP: dict[EquippedSlot, list[EquippedSlot]] = {
    # Если надеваем двуручное оружие (TWO_HAND), оно занимает два слота.
    EquippedSlot.TWO_HAND: [EquippedSlot.MAIN_HAND, EquippedSlot.OFF_HAND],
    # Если надеваем MAIN_HAND, оно конфликтует с двуручным оружием.
    EquippedSlot.MAIN_HAND: [EquippedSlot.TWO_HAND],
}


class InventoryLogicHelpers:
    """
    Класс-помощник, содержащий внутреннюю логику и чистые функции для InventoryService (Layer 3).

    Этот класс призван уменьшить размер и повысить чистоту основного InventoryService,
    инкапсулируя вспомогательные операции, такие как маппинг ресурсов и управление слотами.
    """

    def __init__(self, inventory_repo: IInventoryRepo):
        """
        Инициализирует хелпер.

        Args:
            inventory_repo: Репозиторий инвентаря (для операций чтения/записи),
                            инжектированный из InventoryService.
        """
        self.inventory_repo = inventory_repo
        log.debug("InventoryLogicHelpers | status=initialized")

    @staticmethod
    def map_subtype_to_group(subtype: str) -> ResourceTypeGroup:
        """
        [STATIC] Определяет группу ресурсов для WalletRepo на основе подтипа.
        (Перенесено из InventoryService, сделано статическим).
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
                # Кастинг необходим из-за типа Literal в ResourceTypeGroup
                return cast(ResourceTypeGroup, group)

        return "parts"

    async def get_equipped_map(self, char_id: int) -> dict[EquippedSlot, InventoryItemDTO]:
        """
        Получает все экипированные предметы и преобразует их в словарь
        для быстрого поиска по EquippedSlot.
        (Перенесено из InventoryService).
        """
        # 🔥 Используем инжектированный репозиторий
        equipped_items = await self.inventory_repo.get_items_by_location(char_id, "equipped")
        equipped_map = {EquippedSlot(item.equipped_slot): item for item in equipped_items if item.equipped_slot}
        log.debug(f"InventoryLogicHelpers | action=get_equipped_map count={len(equipped_map)}")
        return equipped_map

    async def handle_slot_conflicts(self, new_item: InventoryItemDTO, target_slot: EquippedSlot) -> None:
        """
        Снимает предметы, конфликтующие с целевым слотом.
        (Перенесено из InventoryService).
        """
        equipped_map = await self.get_equipped_map(new_item.character_id)
        items_to_unequip: list[InventoryItemDTO] = []

        # 1. Снимаем предмет из того же слота (если он есть)
        if target_slot in equipped_map:
            items_to_unequip.append(equipped_map[target_slot])

        # 2. Снимаем предметы, с которыми конфликтует новый слот (двуручное оружие)
        slots_to_check = CONFLICT_MAP.get(target_slot, [])
        for conflict_slot in slots_to_check:
            if conflict_slot in equipped_map:
                items_to_unequip.append(equipped_map[conflict_slot])

        # 3. Обновляем БД
        for old_item in set(items_to_unequip):
            if old_item.item_type in (ItemType.RESOURCE, ItemType.CURRENCY):
                continue
            else:
                await self.inventory_repo.update_fields(
                    old_item.inventory_id, {"location": "inventory", "equipped_slot": None, "quick_slot_position": None}
                )
                log.info(f"Конфликт разрешен: снят {old_item.data.name} из {old_item.equipped_slot}.")

    async def get_quick_slot_limit(self, char_id: int) -> int:
        """
        Рассчитывает максимальное количество доступных Quick Slots.
        (Перенесено из InventoryService).
        """
        # Для расчета лимита требуется агрегация, но для MVP мы берем данные
        # только из пояса (belt). В дальнейшем этот метод будет использовать StatsAggregationService
        # для полного расчета.

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
            log.info(f"QuickSlot | calculated_limit={final_limit} belt='{belt_item.data.name}'")
            return final_limit

    async def unbind_quick_slot(self, item_id: int, char_id: int) -> tuple[bool, str]:
        """
        Убирает предмет из слота быстрого доступа.
        """
        item = await self.inventory_repo.get_item_by_id(item_id)

        if not item or item.character_id != char_id:
            return False, "Предмет не найден или не принадлежит вам."

        if not item.quick_slot_position:
            return False, "Предмет не находится в быстром слоте."

        # Обновляем поле в БД (ставим None)
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
        """
        filtered = []

        for item in items:
            # 1. Фильтрация по секции (Инвентарь vs Экипировка)
            if (section == "inventory" and item.location != "inventory") or (
                section == "equipment" and item.location != "equipped"
            ):
                continue

            # 2. Фильтрация по категории (Вкладки: Оружие, Ресурсы и т.д.)
            # Если категория "all" - показываем всё в этой секции
            if category == "all":
                filtered.append(item)
                continue

            # Логика сопоставления category (из фронта) с item_type или subtype
            # Пример простой проверки:
            if item.item_type.lower() == category.lower():
                filtered.append(item)
            # Тут можно добавить более сложную логику, если categories отличаются от item_type

        return filtered
