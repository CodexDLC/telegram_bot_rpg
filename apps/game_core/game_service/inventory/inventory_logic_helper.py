#

from loguru import logger as log

from apps.common.database.db_contract.i_inventory_repo import IInventoryRepo

# Импортируем Literal типов из контракта, чтобы избежать циклических зависимостей с ORM
from apps.common.database.db_contract.i_wallet_repo import ResourceTypeGroup
from apps.common.schemas_dto import EquippedSlot, InventoryItemDTO, ItemType

# Карта конфликтов слотов (Двуручное занимает обе руки)
CONFLICT_MAP: dict[EquippedSlot, list[EquippedSlot]] = {
    EquippedSlot.TWO_HAND: [EquippedSlot.MAIN_HAND, EquippedSlot.OFF_HAND],
    EquippedSlot.MAIN_HAND: [EquippedSlot.TWO_HAND],
}


class InventoryLogicHelpers:
    """
    Класс-помощник, содержащий внутреннюю логику и чистые функции для InventoryService (Layer 3).
    Отвечает за:
    1. Определение групп ресурсов (Экономика).
    2. Разрешение конфликтов экипировки.
    3. Фильтрацию списков предметов.
    """

    def __init__(self, inventory_repo: IInventoryRepo):
        self.inventory_repo = inventory_repo
        log.debug("InventoryLogicHelpers | status=initialized")

    @staticmethod
    def get_resource_group(item_id: str) -> ResourceTypeGroup:
        """
        [NEW ARCHITECTURE]
        Определяет, в какую группу (столп) кошелька попадает предмет по его ID.

        Rules:
        1. currency_... -> 'currency' (Пыль, Осколки)
        2. res_...      -> 'resources' (Сырье: Руда, Шкуры, Травы, Дерево)
        3. essence_...  -> 'resources' (Природные эссенции)
        4. mat_...      -> 'components' (Слитки, Доски, Кожа)
        5. part_...     -> 'components' (Лезвия, Рукояти)
        """
        # 1. Валюта
        if item_id.startswith("currency_") or item_id in ("dust", "shards", "cores"):
            return "currency"

        # 2. Сырьё (Resources) - то, что добыли
        if item_id.startswith("res_") or item_id.startswith("essence_"):
            return "resources"

        # 3. Компоненты (Components) - то, что скрафтили/разобрали
        if item_id.startswith("mat_") or item_id.startswith("part_"):
            return "components"

        # Fallback: Если ID нестандартный, по умолчанию считаем компонентом
        return "components"

    @staticmethod
    def map_subtype_to_group(subtype: str) -> ResourceTypeGroup:
        """
        Обертка для совместимости. Если где-то передается subtype вместо item_id,
        мы всё равно используем новую логику get_resource_group.
        """
        # Превращаем строку в Literal принудительно, чтобы IDE не ругалась
        return InventoryLogicHelpers.get_resource_group(subtype)

    async def get_filtered_items(
        self, items: list[InventoryItemDTO], section: str, category: str
    ) -> list[InventoryItemDTO]:
        """
        Фильтрует предметы для отображения в инвентаре (Frontend API).

        Args:
            items: Список всех предметов.
            section: Раздел ('inventory', 'equip', 'resource').
            category: Уточнение ('all', 'weapon', 'resources', 'head_armor'...).
        """
        filtered = []

        for item in items:
            # 1. Фильтрация по Секции (Локация предмета)
            # Если раздел "Инвентарь" или "Надеть" -> показываем только то, что в сумке
            if section in ("inventory", "equip") and item.location != "inventory":
                continue

            # Если раздел "Кукла" (обзор снаряжения) -> показываем только надетое
            # (Хотя обычно для куклы используется get_equipped_map, но оставим для универсальности списков)

            # 2. Фильтрация по Категории (Тип фильтра)
            if category == "all":
                filtered.append(item)
                continue

            # А. Ресурсы: Фильтр по Группе (Сырье vs Компоненты)
            if section == "resource":
                # item.subtype здесь выступает как item_id (например 'res_iron_ore')
                item_group = self.get_resource_group(item.subtype)

                # Если категория 'resources' или 'components' совпадает с группой предмета
                if item_group == category:
                    filtered.append(item)
                continue

            # Б. Экипировка: Фильтр по Слоту (если category == 'head_armor' и т.д.)
            # Используется при выборе предмета для конкретного слота
            if (
                hasattr(item.data, "valid_slots")
                and item.data.valid_slots
                and any(str(s) == category for s in item.data.valid_slots)
            ):
                filtered.append(item)
                continue

            # В. Экипировка: Фильтр по Типу (weapon, armor, accessory) - табы инвентаря
            if hasattr(item.item_type, "value") and item.item_type.value == category:
                filtered.append(item)
                continue

            # Г. Прямое совпадение (fallback)
            if str(item.item_type) == category:
                filtered.append(item)
                continue

        return filtered

    async def get_equipped_map(self, char_id: int) -> dict[EquippedSlot, InventoryItemDTO]:
        """Возвращает словарь {Слот: Предмет} для экипированных вещей."""
        equipped_items = await self.inventory_repo.get_items_by_location(char_id, "equipped")
        equipped_map = {EquippedSlot(item.equipped_slot): item for item in equipped_items if item.equipped_slot}
        return equipped_map

    async def handle_slot_conflicts(self, new_item: InventoryItemDTO, target_slot: EquippedSlot) -> None:
        """Снимает предметы, конфликтующие с новым (например, снимает щит, если надеваем двуручник)."""
        equipped_map = await self.get_equipped_map(new_item.character_id)
        items_to_unequip: list[InventoryItemDTO] = []

        # 1. Если слот занят -> снимаем старое
        if target_slot in equipped_map:
            items_to_unequip.append(equipped_map[target_slot])

        # 2. Проверяем связанные конфликты
        slots_to_check = CONFLICT_MAP.get(target_slot, [])
        for conflict_slot in slots_to_check:
            if conflict_slot in equipped_map:
                items_to_unequip.append(equipped_map[conflict_slot])

        # 3. Применяем снятие
        for old_item in set(items_to_unequip):
            if old_item.item_type in (ItemType.RESOURCE, ItemType.CURRENCY):
                continue

            await self.inventory_repo.update_fields(
                old_item.inventory_id, {"location": "inventory", "equipped_slot": None, "quick_slot_position": None}
            )
            log.info(
                f"InventoryLogic | Conflict resolved: unequipped {old_item.data.name} from {old_item.equipped_slot}"
            )

    async def get_quick_slot_limit(self, char_id: int) -> int:
        """Считает лимит быстрых слотов (база + бонусы от пояса)."""
        equipped_map = await self.get_equipped_map(char_id)
        belt_item = equipped_map.get(EquippedSlot.BELT_ACCESSORY)

        base_quick_slot_limit = 0  # База 0, нужен пояс

        if not belt_item or belt_item.item_type in (ItemType.RESOURCE, ItemType.CURRENCY):
            return base_quick_slot_limit

        current_limit = 0
        if belt_item.data.bonuses:
            # Ищем бонус 'quick_slot_capacity' в данных предмета
            capacity = belt_item.data.bonuses.get("quick_slot_capacity", 0)
            if isinstance(capacity, (int, float)):
                current_limit = int(capacity)

        return max(base_quick_slot_limit, current_limit)

    async def unbind_quick_slot(self, item_id: int, char_id: int) -> tuple[bool, str]:
        """Убирает предмет из слота быстрого доступа."""
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
