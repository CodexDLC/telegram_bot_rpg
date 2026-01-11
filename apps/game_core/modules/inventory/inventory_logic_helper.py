# from typing import Literal
#
# from apps.common.database.db_contract.i_inventory_repo import IInventoryRepo
# from apps.common.schemas_dto import EquippedSlot, InventoryItemDTO, ItemType
# from apps.common.schemas_dto.item_dto import AccessoryData, ArmorData, ItemRarity, WeaponData
#
#
# class InventoryLogicHelpers:
#     """
#     Статические методы и чистая логика для работы с инвентарем.
#     """
#
#     def __init__(self, inventory_repo: IInventoryRepo):
#         self.inventory_repo = inventory_repo
#
#     @staticmethod
#     def get_resource_group(resource_key: str) -> Literal["currency", "resources", "components"]:
#         if "currency_" in resource_key:
#             return "currency"
#         if "res_" in resource_key:
#             return "resources"
#         return "components"
#
#     @staticmethod
#     async def filter_and_sort_items(
#         items: list[InventoryItemDTO],
#         section: str,
#         category: str | None = None,
#     ) -> list[InventoryItemDTO]:
#         # Явно указываем тип списка, чтобы mypy не сужал его
#         filtered: list[InventoryItemDTO] = []
#
#         if section == "equip":
#             allowed_types = [ItemType.WEAPON, ItemType.ARMOR, ItemType.ACCESSORY]
#             filtered = [item for item in items if item.item_type in allowed_types]
#         elif section == "resource":
#             allowed_types = [ItemType.RESOURCE, ItemType.CURRENCY]
#             filtered = [item for item in items if item.item_type in allowed_types]
#         elif section == "consumable":
#             filtered = [item for item in items if item.item_type == ItemType.CONSUMABLE]
#         else:
#             filtered = items
#
#         if category:
#             temp_filtered: list[InventoryItemDTO] = []
#             for item in filtered:
#                 if category in ["garment", "accessory"] and isinstance(
#                     item.data, (WeaponData, ArmorData, AccessoryData)
#                 ):
#                     slot_str = str(item.data.valid_slots[0])
#                     if category in slot_str:
#                         temp_filtered.append(item)
#                         continue
#
#                 if str(item.item_type) == category:
#                     temp_filtered.append(item)
#                     continue
#
#                 if item.subtype == category:
#                     temp_filtered.append(item)
#                     continue
#
#             filtered = temp_filtered
#
#         rarity_order = {
#             ItemRarity.ABSOLUTE: 0,
#             ItemRarity.EXOTIC: 1,
#             ItemRarity.MYTHIC: 2,
#             ItemRarity.LEGENDARY: 3,
#             ItemRarity.EPIC: 4,
#             ItemRarity.RARE: 5,
#             ItemRarity.UNCOMMON: 6,
#             ItemRarity.COMMON: 7,
#         }
#         filtered.sort(key=lambda x: (rarity_order.get(x.rarity, 99), x.data.name))
#
#         return filtered
#
#     async def get_quick_slot_limit(self, char_id: int) -> int:
#         base_quick_slot_limit = 0
#         current_limit = 0
#
#         equipped_items = await self.inventory_repo.get_equipped_items(char_id)
#         belt_item = next(
#             (item for item in equipped_items if item.equipped_slot == EquippedSlot.BELT_ACCESSORY),
#             None,
#         )
#
#         if belt_item:
#             capacity = belt_item.data.bonuses.get("quick_slot_capacity", 0)
#             current_limit = int(capacity)
#
#         return max(base_quick_slot_limit, current_limit)
#
#     async def unbind_quick_slot(self, item_id: int, char_id: int) -> tuple[bool, str]:
#         item = await self.inventory_repo.get_item_by_id(item_id)
#         if not item or item.character_id != char_id:
#             return False, "Предмет не найден."
#
#         if not item.quick_slot_position:
#             return False, "Предмет не находится в быстром слоте."
#
#         success = await self.inventory_repo.update_fields(item_id, {"quick_slot_position": None})
#         if success:
#             return True, f"{item.data.name} убран из быстрого слота."
#         return False, "Ошибка базы данных."
