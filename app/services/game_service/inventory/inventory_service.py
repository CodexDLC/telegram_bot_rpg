# app/services/game_service/inventory/inventory_service.py
from sqlalchemy.ext.asyncio import AsyncSession

from app.resources.schemas_dto.item_dto import InventoryItemDTO
from database.repositories import get_inventory_repo


class InventoryService:
    """
    Сервис бизнес-логики инвентаря.
    Отвечает за манипуляции с предметами (надеть, снять, удалить, переместить)
    и пересчет характеристик персонажа.
    """

    def __init__(self, char_id: int, session: AsyncSession):
        """
        Инициализация с сессией БД и репозиториями.
        """
        self.char_id = char_id
        self.session = session
        self.inventory_repo = get_inventory_repo(self.session)

    async def get_character_inventory(self) -> list[InventoryItemDTO]:
        """
        Получает полный список предметов персонажа (из всех локаций или только из рюкзака?).
        Возможно, стоит фильтровать только 'inventory' и 'equipped'.
        """
        pass

    async def equip_item(self, item_id: int) -> bool:
        """
        Попытка надеть предмет.
        1. Проверяет, существует ли предмет и принадлежит ли он char_id.
        2. Проверяет требования (уровень, класс, статы).
        3. Проверяет слот (занят ли?). Если занят — вызывает unequip_item для старой вещи.
        4. Меняет location предмета на 'equipped'.
        5. Триггерит пересчет статов через StatsAggregationService (или просто сбрасывает кэш).
        """
        pass

    async def unequip_item(self, item_id: int) -> bool:
        """
        Снятие предмета.
        1. Проверяет, надет ли предмет.
        2. Проверяет, есть ли место в инвентаре (если у нас лимит слотов).
        3. Меняет location на 'inventory'.
        4. Триггерит пересчет статов.
        """
        pass

    async def drop_item(self, item_id: int) -> bool:
        """
        Удаление (выбрасывание/распыление) предмета.
        В MVP — просто удаление из БД.
        """
        pass

    async def get_item_details(self, item_id: int) -> InventoryItemDTO | None:
        """
        Получение одного предмета для детального просмотра.
        Нужна проверка владельца (char_id).
        """
        pass
