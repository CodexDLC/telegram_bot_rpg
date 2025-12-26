from loguru import logger as log

from apps.common.schemas_dto import EquippedSlot, InventoryItemDTO, ItemType
from apps.common.schemas_dto.inventory_dto import InventorySessionDTO


class EquipmentLogic:
    """
    Логика работы с экипировкой (Кукла персонажа).
    Работает с сессией в памяти (InventorySessionDTO).
    """

    def get_equipped_items(self, session: InventorySessionDTO) -> list[InventoryItemDTO]:
        """Возвращает список всех надетых предметов."""
        return [item for item in session.items.values() if item.location == "equipped"]

    def get_candidates_for_slot(self, session: InventorySessionDTO, slot: EquippedSlot) -> list[InventoryItemDTO]:
        """
        Возвращает список предметов из инвентаря, которые можно надеть в указанный слот.
        """
        candidates = []
        for item in session.items.values():
            if item.location != "inventory":
                continue

            if item.item_type not in (ItemType.WEAPON, ItemType.ARMOR, ItemType.ACCESSORY):
                continue

            if hasattr(item.data, "valid_slots"):
                valid_slots = item.data.valid_slots

                if slot.value in valid_slots:
                    candidates.append(item)
                    continue

                if "ring" in valid_slots and slot.value in ("ring_1", "ring_2"):
                    candidates.append(item)
                    continue

                if "one_hand_weapon" in valid_slots and slot.value in ("main_hand", "off_hand"):
                    candidates.append(item)
                    continue

        return candidates

    def equip_item(
        self, session: InventorySessionDTO, item_id: int, target_slot: EquippedSlot | None = None
    ) -> tuple[bool, str]:
        """
        Надевает предмет.
        Если target_slot не указан, пытается определить его автоматически.
        """
        item = session.items.get(item_id)
        if not item:
            return False, "Предмет не найден."

        # Авто-определение слота
        if target_slot is None:
            if not hasattr(item.data, "valid_slots") or not item.data.valid_slots:
                return False, "Этот предмет нельзя надеть."

            # Берем первый валидный слот
            # TODO: Улучшить логику для колец (искать свободный слот)
            first_slot_str = item.data.valid_slots[0]

            # Если это кольцо, пробуем найти свободный слот
            if "ring" in first_slot_str:
                target_slot = self._find_free_ring_slot(session)
            else:
                try:
                    target_slot = EquippedSlot(first_slot_str)
                except ValueError:
                    # Если в valid_slots записана категория (например 'one_hand_weapon'), маппим на дефолт
                    if "one_hand_weapon" in first_slot_str:
                        target_slot = EquippedSlot.MAIN_HAND
                    else:
                        return False, f"Неизвестный слот: {first_slot_str}"

        # 1. Снимаем конфликтующие предметы
        self._unequip_conflicting_items(session, target_slot)

        # 2. Надеваем новый
        item.location = "equipped"
        item.equipped_slot = target_slot
        item.quick_slot_position = None

        log.info(f"EquipLogic | Equipped item {item_id} to {target_slot}")
        return True, f"Надето: {item.data.name}"

    def unequip_item(self, session: InventorySessionDTO, item_id: int) -> tuple[bool, str]:
        """Снимает предмет."""
        item = session.items.get(item_id)
        if not item:
            return False, "Предмет не найден."

        if item.location != "equipped":
            return False, "Предмет не надет."

        item.location = "inventory"
        item.equipped_slot = None

        log.info(f"EquipLogic | Unequipped item {item_id}")
        return True, f"Снято: {item.data.name}"

    def _unequip_conflicting_items(self, session: InventorySessionDTO, target_slot: EquippedSlot):
        """
        Находит и снимает предметы, которые мешают надеть новый.
        """
        equipped = self.get_equipped_items(session)
        to_unequip = []

        if target_slot == EquippedSlot.TWO_HAND:
            to_unequip.extend(
                [
                    i
                    for i in equipped
                    if i.equipped_slot in (EquippedSlot.MAIN_HAND, EquippedSlot.OFF_HAND, EquippedSlot.TWO_HAND)
                ]
            )
        elif target_slot in (EquippedSlot.MAIN_HAND, EquippedSlot.OFF_HAND):
            to_unequip.extend([i for i in equipped if i.equipped_slot == EquippedSlot.TWO_HAND])
            to_unequip.extend([i for i in equipped if i.equipped_slot == target_slot])
        else:
            to_unequip.extend([i for i in equipped if i.equipped_slot == target_slot])

        for item in to_unequip:
            item.location = "inventory"
            item.equipped_slot = None

    def _find_free_ring_slot(self, session: InventorySessionDTO) -> EquippedSlot:
        """Ищет свободный слот для кольца, иначе возвращает RING_1."""
        equipped = self.get_equipped_items(session)
        ring1_busy = any(i.equipped_slot == EquippedSlot.RING_1 for i in equipped)
        ring2_busy = any(i.equipped_slot == EquippedSlot.RING_2 for i in equipped)

        if not ring1_busy:
            return EquippedSlot.RING_1
        if not ring2_busy:
            return EquippedSlot.RING_2
        return EquippedSlot.RING_1  # Если оба заняты, заменяем первое
