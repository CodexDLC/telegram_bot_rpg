from typing import Any

from pydantic import computed_field

from backend.domains.internal_systems.context_assembler.schemas.base import BaseTempContext


class InventoryTempContext(BaseTempContext):
    """
    Контекст для UI инвентаря.
    """

    @computed_field(alias="items_by_slot")
    def inventory_view(self) -> dict[str, Any]:
        if not self.core_inventory:
            return {}

        slots = {}
        for item in self.core_inventory:
            # item может быть dict или DTO
            item_data = item.model_dump() if hasattr(item, "model_dump") else item

            if item_data.get("location") == "equipped" and item_data.get("equipped_slot"):
                slots[item_data["equipped_slot"]] = {
                    "item_id": item_data.get("inventory_id"),
                    "name": item_data.get("data", {}).get("name", "Unknown"),
                    "type": item_data.get("item_type"),
                    "rarity": item_data.get("rarity"),
                }
        return slots

    @computed_field(alias="items_by_type")
    def type_groups(self) -> dict[str, list]:
        if not self.core_inventory:
            return {}

        groups: dict[str, list] = {
            "weapon": [],
            "armor": [],
            "consumable": [],
            "material": [],
            "other": [],
        }

        for item in self.core_inventory:
            item_data = item.model_dump() if hasattr(item, "model_dump") else item
            item_type = item_data.get("item_type", "other")

            if item_type not in groups:
                item_type = "other"

            groups[item_type].append(
                {
                    "item_id": item_data.get("inventory_id"),
                    "name": item_data.get("data", {}).get("name", "Unknown"),
                    "quantity": item_data.get("quantity"),
                    "rarity": item_data.get("rarity"),
                }
            )
        return groups

    @computed_field(alias="wallet_display")
    def wallet_view(self) -> dict[str, Any]:
        if not self.core_wallet:
            return {"currency": {}, "resources": {}, "components": {}}

        return {
            "currency": self.core_wallet.get("currency", {}),
            "resources": self.core_wallet.get("resources", {}),
            "components": self.core_wallet.get("components", {}),
        }
