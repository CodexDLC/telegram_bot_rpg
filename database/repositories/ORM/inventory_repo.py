from typing import Any

from loguru import logger as log
from pydantic import TypeAdapter
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import SYSTEM_CHAR_ID
from app.resources.schemas_dto.item_dto import (
    InventoryItemDTO,
)
from database.db_contract.i_inventory_repo import IInventoryRepo
from database.model_orm.inventory import InventoryItem


class InventoryRepo(IInventoryRepo):
    def __init__(self, session: AsyncSession):
        self.session = session
        # Адаптер для валидации полиморфного DTO
        self.dto_adapter: TypeAdapter[InventoryItemDTO] = TypeAdapter(InventoryItemDTO)

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
        Создает НОВЫЙ предмет (рождение от ЛЛМ).
        """
        new_inv_item = InventoryItem(
            character_id=character_id,
            item_type=item_type,
            subtype=subtype,
            rarity=rarity,
            location=location,
            item_data=item_data,
        )

        try:
            self.session.add(new_inv_item)
            await self.session.flush()
            log.debug(f"Сгенерирован новый предмет ID={new_inv_item.id} для char_id={character_id}")
            return new_inv_item.id
        except SQLAlchemyError as e:
            log.exception(f"Ошибка создания предмета: {e}")
            raise

    async def get_system_item_for_reuse(
        self, item_type: str, rarity: str, subtype: str | None = None
    ) -> InventoryItemDTO | None:
        """
        🔥 КЛЮЧЕВАЯ ЛОГИКА ЭКОНОМИКИ:
        Ищет "бесхозный" предмет в инвентаре Системы, чтобы не генерировать новый.
        Например: "Нужен Common Sword для награды".
        """
        # Ищем предметы, которые принадлежат Системе (SYSTEM_CHAR_ID)
        query = select(InventoryItem).where(
            InventoryItem.character_id == SYSTEM_CHAR_ID,
            InventoryItem.item_type == item_type,
            InventoryItem.rarity == rarity,
        )

        if subtype:
            query = query.where(InventoryItem.subtype == subtype)

        # Берем случайный (чтобы не выдавать всегда один и тот же, если их много)
        query = query.order_by(func.random()).limit(1)

        result = await self.session.execute(query)
        item = result.scalar_one_or_none()

        if item:
            log.info(f"♻️ Найден системный предмет ID={item.id} для повторного использования.")
            return self._to_dto(item)

        log.debug("Системный предмет не найден. Требуется генерация ЛЛМ.")
        return None

    async def transfer_item(self, inventory_id: int, new_owner_id: int, new_location: str = "inventory") -> bool:
        """
        Передает предмет от одного владельца другому.
        Используется для:
        - Выдачи награды (System -> Player)
        - Покупки в магазине (System -> Player)
        - Продажи в магазин (Player -> System)
        """
        stmt = (
            update(InventoryItem)
            .where(InventoryItem.id == inventory_id)
            .values(character_id=new_owner_id, location=new_location)
        )
        try:
            await self.session.execute(stmt)
            log.info(f"Предмет {inventory_id} передан владельцу {new_owner_id} (loc={new_location})")
            return True
        except SQLAlchemyError as e:
            log.exception(f"Ошибка передачи предмета: {e}")
            return False

    # --- Стандартные методы (Get, Move, Delete) ---

    async def get_all_items(self, character_id: int) -> list[InventoryItemDTO]:
        stmt = select(InventoryItem).where(InventoryItem.character_id == character_id)
        result = await self.session.execute(stmt)
        return [self._to_dto(item) for item in result.scalars().all()]

    async def get_items_by_location(self, character_id: int, location: str) -> list[InventoryItemDTO]:
        stmt = select(InventoryItem).where(
            InventoryItem.character_id == character_id, InventoryItem.location == location
        )
        result = await self.session.execute(stmt)
        items = result.scalars().all()
        return [self._to_dto(item) for item in items]

    async def get_item_by_id(self, inventory_id: int) -> InventoryItemDTO | None:
        stmt = select(InventoryItem).where(InventoryItem.id == inventory_id)
        result = await self.session.execute(stmt)
        item = result.scalar_one_or_none()
        if item:
            return self._to_dto(item)
        return None

    async def move_item(self, inventory_id: int, new_location: str) -> bool:
        stmt = update(InventoryItem).where(InventoryItem.id == inventory_id).values(location=new_location)
        try:
            await self.session.execute(stmt)
            return True
        except SQLAlchemyError:
            return False

    async def delete_item(self, inventory_id: int) -> bool:
        """Распыление / Уничтожение"""
        stmt = delete(InventoryItem).where(InventoryItem.id == inventory_id)
        try:
            await self.session.execute(stmt)
            log.info(f"Предмет {inventory_id} распылен/удален из мира.")
            return True
        except SQLAlchemyError:
            return False

    async def update_item_data(self, inventory_id: int, new_data: dict[str, Any]) -> bool:
        stmt = update(InventoryItem).where(InventoryItem.id == inventory_id).values(item_data=new_data)
        try:
            await self.session.execute(stmt)
            return True
        except SQLAlchemyError:
            return False

    def _to_dto(self, orm_item: InventoryItem) -> InventoryItemDTO:
        # Собираем словарь, который будет валидироваться Pydantic
        # Он должен содержать поле-дискриминатор (item_type)
        dto_dict = {
            "inventory_id": orm_item.id,
            "item_type": orm_item.item_type,
            "subtype": orm_item.subtype,
            "rarity": orm_item.rarity,
            "data": orm_item.item_data,  # Вся полезная нагрузка (name, damage, bonuses)
        }

        # Используем TypeAdapter для валидации полиморфного типа
        # Он сам выберет нужный DTO (WeaponItemDTO, ArmorItemDTO) по полю "item_type"
        return self.dto_adapter.validate_python(dto_dict)
