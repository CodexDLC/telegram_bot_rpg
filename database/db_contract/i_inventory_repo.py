# database/db_contract/i_inventory_repo.py
from abc import ABC, abstractmethod
from typing import Any

from app.resources.schemas_dto.item_dto import InventoryItemDTO


class IInventoryRepo(ABC):
    """
    Интерфейс для работы с ЕДИНСТВЕННОЙ таблицей предметов (InventoryItem).
    """

    @abstractmethod
    async def create_item(
        self,
        character_id: int,
        item_type: str,
        subtype: str,
        rarity: str,
        item_data: dict[str, Any],
        location: str = "inventory",
        quantity: int = 1,
    ) -> int:
        """Создает новый уникальный предмет в базе данных (INSERT)."""
        pass

    # 🔥 ДОБАВЛЕНО: Метод для ресайклинга
    @abstractmethod
    async def get_system_item_for_reuse(
        self, item_type: str, rarity: str, subtype: str | None = None
    ) -> InventoryItemDTO | None:
        """
        Ищет предмет, принадлежащий Системе, для повторного использования.
        """
        pass

    # 🔥 ДОБАВЛЕНО: Метод для передачи предмета
    @abstractmethod
    async def transfer_item(self, inventory_id: int, new_owner_id: int, new_location: str = "inventory") -> bool:
        """
        Меняет владельца предмета (System -> Player или наоборот).
        """
        pass

    @abstractmethod
    async def get_all_items(self, character_id: int) -> list[InventoryItemDTO]:
        pass

    @abstractmethod
    async def get_items_by_location(self, character_id: int, location: str) -> list[InventoryItemDTO]:
        pass

    @abstractmethod
    async def get_item_by_id(self, inventory_id: int) -> InventoryItemDTO | None:
        pass

    @abstractmethod
    async def move_item(self, inventory_id: int, new_location: str) -> bool:
        pass

    @abstractmethod
    async def delete_item(self, inventory_id: int) -> bool:
        pass

    @abstractmethod
    async def update_item_data(self, inventory_id: int, new_data: dict[str, Any]) -> bool:
        pass
