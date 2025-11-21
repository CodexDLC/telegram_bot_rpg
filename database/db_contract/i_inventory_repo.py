# database/db_contract/i_inventory_repo.py
from abc import ABC, abstractmethod
from typing import Any

from app.resources.schemas_dto.item_dto import InventoryItemDTO


class IInventoryRepo(ABC):
    """
    Интерфейс для работы с ЕДИНСТВЕННОЙ таблицей предметов (InventoryItem).

    В архитектуре "Pure Instance" (Чистый Экземпляр):
    1. Таблицы 'items' (шаблонов) НЕ существует.
    2. Вся информация о предмете (имя, урон, бонусы, описание) хранится
       в поле `item_data` (JSON) прямо в таблице инвентаря.
    3. Поля `item_type`, `subtype`, `rarity` в таблице нужны только
       для быстрой фильтрации и поиска (индексации), они дублируют данные из JSON.
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
        Создает новый уникальный предмет в базе данных (INSERT).

        В этой системе каждый меч, даже одинаковый по названию,
        является уникальной строкой в БД.

        Args:
            character_id (int): ID владельца (Игрок или Система/ISKIN).
            item_type (str): Тип предмета для поиска (weapon, armor...).
            subtype (str): Подтип для поиска (sword, chest_plate...).
            rarity (str): Редкость для поиска (common, epic...).
            item_data (dict): ГЛАВНОЕ ПОЛЕ. Полный JSON-объект предмета.
                              Содержит всё: name, stats, bonuses, enchant_level.
                              Формируется из DTO (model_dump).
            location (str): Где создать? ("inventory", "auction", "shop_npc_1").
            quantity (int): Количество (актуально для ресурсов/расходников).

        Returns:
            int: Уникальный ID созданной вещи (inventory_id).
        """
        pass

    @abstractmethod
    async def get_all_items(self, character_id: int) -> list[InventoryItemDTO]:
        """
        Загружает ВСЕ предметы персонажа (из всех локаций: рюкзак, кукла, банк).
        Реализация должна автоматически конвертировать JSON из БД в Pydantic DTO.
        """
        pass

    @abstractmethod
    async def get_items_by_location(self, character_id: int, location: str) -> list[InventoryItemDTO]:
        """
        Загружает предметы только из конкретного "кармана".

        Используется для:
        - "equipped": Чтобы калькулятор статов посчитал бонусы.
        - "inventory": Чтобы показать игроку содержимое рюкзака.
        - "auction": Чтобы показать выставленные лоты.
        """
        pass

    @abstractmethod
    async def get_item_by_id(self, inventory_id: int) -> InventoryItemDTO | None:
        """
        Получает конкретный предмет по его уникальному ID (inventory_id).
        Нужен для действий с конкретным предметом (Надеть, Продать, Выбросить).
        """
        pass

    @abstractmethod
    async def move_item(self, inventory_id: int, new_location: str) -> bool:
        """
        Меняет поле `location` у предмета.

        Примеры использования:
        - Надевание: "inventory" -> "equipped"
        - Снятие: "equipped" -> "inventory"
        - Выставление на аукцион: "inventory" -> "auction"
        - Продажа NPC (передача системе): меняется также владелец (отдельный метод transfer).
        """
        pass

    @abstractmethod
    async def delete_item(self, inventory_id: int) -> bool:
        """
        Физически удаляет запись из БД.
        Используется при: распылении, использовании расходников, удалении мусора.
        """
        pass

    @abstractmethod
    async def update_item_data(self, inventory_id: int, new_data: dict[str, Any]) -> bool:
        """
        Обновляет поле `item_data` (JSON).

        Используется, когда меняются свойства самого предмета:
        - Заточка (изменился enchant_level).
        - Поломка/Починка (изменилась durability).
        - Реролл бонусов (изменились bonuses).
        """
        pass
