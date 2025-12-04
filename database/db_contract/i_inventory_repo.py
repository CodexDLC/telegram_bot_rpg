from abc import ABC, abstractmethod
from typing import Any

from app.resources.schemas_dto.item_dto import InventoryItemDTO


class IInventoryRepo(ABC):
    """
    Интерфейс для работы с таблицей предметов (`InventoryItem`).

    Определяет контракт для создания, получения, перемещения,
    обновления и удаления предметов в инвентаре.
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
        """
        Создает новый уникальный предмет в базе данных.

        Args:
            character_id: Идентификатор персонажа, которому принадлежит предмет.
            item_type: Тип предмета (например, "weapon", "armor").
            subtype: Подтип предмета (например, "sword", "heavy_armor").
            rarity: Редкость предмета ("common", "rare").
            item_data: Словарь с детальными данными предмета (JSON-payload).
            location: Местонахождение предмета ("inventory", "equipped").
            quantity: Количество предметов (для стакающихся).

        Returns:
            Идентификатор созданного предмета.
        """
        pass

    @abstractmethod
    async def get_system_item_for_reuse(
        self, item_type: str, rarity: str, subtype: str | None = None
    ) -> InventoryItemDTO | None:
        """
        Ищет предмет, принадлежащий Системе (character_id = SYSTEM_USER_ID),
        для повторного использования в качестве шаблона или для выдачи.

        Args:
            item_type: Тип предмета.
            rarity: Редкость предмета.
            subtype: Опциональный подтип предмета.

        Returns:
            DTO `InventoryItemDTO`, если предмет найден, иначе None.
        """
        pass

    @abstractmethod
    async def transfer_item(self, inventory_id: int, new_owner_id: int, new_location: str = "inventory") -> bool:
        """
        Изменяет владельца предмета и его местоположение.

        Используется для передачи предметов от Системы игроку или между игроками.

        Args:
            inventory_id: Идентификатор предмета.
            new_owner_id: Идентификатор нового владельца.
            new_location: Новое местоположение предмета.

        Returns:
            True, если предмет успешно передан, иначе False.
        """
        pass

    @abstractmethod
    async def get_all_items(self, character_id: int) -> list[InventoryItemDTO]:
        """
        Возвращает все предметы, принадлежащие указанному персонажу.

        Args:
            character_id: Идентификатор персонажа.

        Returns:
            Список DTO `InventoryItemDTO`.
        """
        pass

    @abstractmethod
    async def get_items_by_location(self, character_id: int, location: str) -> list[InventoryItemDTO]:
        """
        Возвращает предметы персонажа, находящиеся в указанной локации.

        Args:
            character_id: Идентификатор персонажа.
            location: Местоположение предметов (например, "inventory", "equipped").

        Returns:
            Список DTO `InventoryItemDTO`.
        """
        pass

    @abstractmethod
    async def get_item_by_id(self, inventory_id: int) -> InventoryItemDTO | None:
        """
        Возвращает предмет по его уникальному идентификатору.

        Args:
            inventory_id: Уникальный идентификатор предмета.

        Returns:
            DTO `InventoryItemDTO`, если предмет найден, иначе None.
        """
        pass

    @abstractmethod
    async def move_item(self, inventory_id: int, new_location: str) -> bool:
        """
        Перемещает предмет в новое местоположение.

        Args:
            inventory_id: Идентификатор предмета.
            new_location: Новое местоположение предмета.

        Returns:
            True, если предмет успешно перемещен, иначе False.
        """
        pass

    @abstractmethod
    async def delete_item(self, inventory_id: int) -> bool:
        """
        Удаляет предмет из базы данных.

        Args:
            inventory_id: Идентификатор предмета.

        Returns:
            True, если предмет успешно удален, иначе False.
        """
        pass

    @abstractmethod
    async def update_item_data(self, inventory_id: int, new_data: dict[str, Any]) -> bool:
        """
        Обновляет JSON-поле `item_data` для указанного предмета.

        Args:
            inventory_id: Идентификатор предмета.
            new_data: Словарь с новыми данными для JSON-поля.

        Returns:
            True, если данные успешно обновлены, иначе False.
        """
        pass

    @abstractmethod
    async def update_fields(self, inventory_id: int, update_data: dict[str, Any]) -> bool:
        """
        Обновляет несколько полей предмета одним вызовом.

        Args:
            inventory_id: ID предмета.
            update_data: Словарь {поле: новое_значение}.

        Returns: True, если обновлено, иначе False.
        """
        pass
