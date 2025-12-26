from collections.abc import Sequence

from apps.common.schemas_dto import InventoryItemDTO, ItemType, QuickSlot
from apps.common.schemas_dto.inventory_dto import InventorySessionDTO
from apps.common.schemas_dto.item_dto import (
    AccessoryData,
    ArmorData,
    ItemRarity,
    ResourceData,
    ResourceItemDTO,
    WeaponData,
)
from apps.game_core.resources.game_data.items import get_item_data


class BagLogic:
    """
    Логика работы с сумкой (Инвентарем).
    Фильтрация, сортировка, удаление, быстрые слоты.
    """

    def get_items(
        self, session: InventorySessionDTO, section: str, category: str | None = None
    ) -> Sequence[InventoryItemDTO]:
        """
        Возвращает отфильтрованный и отсортированный список предметов.
        Включает в себя как инстансы предметов, так и ресурсы из кошелька (если section='resource').
        """
        # 1. Берем предметы-инстансы из инвентаря (не надетые)
        items_list: list[InventoryItemDTO] = [i for i in session.items.values() if i.location == "inventory"]

        # 2. Если запрашиваем ресурсы, добавляем их из кошелька (Wallet)
        if section == "resource":
            wallet_items = self._get_wallet_items(session)
            items_list.extend(wallet_items)

        # 3. Фильтрация по секции (Вкладке)
        filtered: list[InventoryItemDTO] = []
        if section == "equip":
            allowed = (ItemType.WEAPON, ItemType.ARMOR, ItemType.ACCESSORY)
            # Explicitly cast to list[InventoryItemDTO] to avoid invariance issues
            filtered = [i for i in items_list if i.item_type in allowed]
        elif section == "resource":
            allowed_res = (ItemType.RESOURCE, ItemType.CURRENCY)
            filtered = [i for i in items_list if i.item_type in allowed_res]
        elif section == "consumable":
            filtered = [i for i in items_list if i.item_type == ItemType.CONSUMABLE]
        else:
            filtered = items_list

        # 4. Фильтрация по категории (Подтипу)
        if category and category != "all":
            temp_filtered: list[InventoryItemDTO] = []
            for item in filtered:
                # Фильтр по слоту (для экипировки)
                if (
                    category in ["garment", "accessory"]
                    and isinstance(item.data, (WeaponData, ArmorData, AccessoryData))
                    and any(category in s for s in item.data.valid_slots)
                ):
                    temp_filtered.append(item)
                    continue

                # Фильтр по типу
                if str(item.item_type) == category:
                    temp_filtered.append(item)
                    continue

                # Фильтр по подтипу
                if item.subtype == category:
                    temp_filtered.append(item)
                    continue

            filtered = temp_filtered

        # 5. Сортировка (по редкости, потом по имени)
        rarity_order = {
            ItemRarity.ABSOLUTE: 0,
            ItemRarity.EXOTIC: 1,
            ItemRarity.MYTHIC: 2,
            ItemRarity.LEGENDARY: 3,
            ItemRarity.EPIC: 4,
            ItemRarity.RARE: 5,
            ItemRarity.UNCOMMON: 6,
            ItemRarity.COMMON: 7,
        }
        filtered.sort(key=lambda x: (rarity_order.get(x.rarity, 99), x.data.name))

        return filtered

    def _get_wallet_items(self, session: InventorySessionDTO) -> list[InventoryItemDTO]:
        """
        Преобразует ресурсы из кошелька в список InventoryItemDTO.
        Использует статические данные для обогащения (имя, описание).
        """
        result: list[InventoryItemDTO] = []

        # Объединяем все словари кошелька
        all_resources = {**session.wallet.currency, **session.wallet.resources, **session.wallet.components}

        for key, amount in all_resources.items():
            if amount <= 0:
                continue

            # Получаем статические данные
            static_data = get_item_data(key)
            if not static_data:
                # Если данных нет, создаем заглушку (чтобы не крашилось)
                name = key
                description = "Unknown resource"
                rarity = ItemRarity.COMMON
            else:
                name = static_data.get("name_ru", key)
                description = static_data.get("narrative_description", "")
                # Редкость можно определить по тиру или конфигу, пока дефолт
                rarity = ItemRarity.COMMON

            # Создаем DTO
            # Используем отрицательный ID или хэш, чтобы отличать от реальных предметов в UI,
            # но так как в InventoryItemDTO id - int, можно использовать hash(key)
            # Но лучше просто 0, так как действия с ними (equip) не нужны.
            # Для уникальности в списках (key) используем hash.
            fake_id = hash(key) % 100000000  # Просто для UI ключей

            item_dto = ResourceItemDTO(
                inventory_id=fake_id,
                character_id=0,  # Не важно
                location="wallet",
                item_type=ItemType.RESOURCE if "currency" not in key else ItemType.CURRENCY,
                subtype="resource",
                rarity=rarity,
                quantity=amount,
                data=ResourceData(
                    name=name,
                    description=description,
                    base_price=static_data.get("base_price", 0) if static_data else 0,
                ),
            )
            result.append(item_dto)

        return result

    def drop_item(self, session: InventorySessionDTO, item_id: int) -> tuple[bool, str]:
        """
        Удаляет предмет из инвентаря (выбрасывает).
        """
        if item_id in session.items:
            item = session.items[item_id]
            if item.location == "equipped":
                return False, "Нельзя выбросить надетый предмет."
            del session.items[item_id]
            return True, f"Выброшено: {item.data.name}"

        # Проверка на ресурс из кошелька (пока нельзя выбрасывать ресурсы через этот метод,
        # так как у них фейковые ID. Для ресурсов нужен отдельный метод drop_resource)
        return False, "Предмет не найден."

    def move_to_quick_slot(self, session: InventorySessionDTO, item_id: int, position: QuickSlot) -> tuple[bool, str]:
        """
        Назначает предмет на быстрый слот.
        """
        item = session.items.get(item_id)
        if not item:
            return False, "Предмет не найден."

        if item.item_type != ItemType.CONSUMABLE:
            return False, "В быстрый слот можно положить только расходники."

        if not getattr(item.data, "is_quick_slot_compatible", False):
            return False, "Этот предмет нельзя использовать быстро."

        max_slots = 4
        pos_index = int(position.value.split("_")[-1])
        if pos_index > max_slots:
            return False, "Слот недоступен."

        for other in session.items.values():
            if other.quick_slot_position == position.value and other.inventory_id != item_id:
                other.quick_slot_position = None

        item.quick_slot_position = position.value

        return True, f"Назначено на {position.name}"
