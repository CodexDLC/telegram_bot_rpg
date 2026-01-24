from collections import defaultdict
from typing import Any

from loguru import logger as log
from pydantic import TypeAdapter
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.database.db_contract.i_inventory_repo import IInventoryRepo
from backend.database.postgres.models.inventory import InventoryItem
from common.schemas.item import (
    InventoryItemDTO,
)


class InventoryRepo(IInventoryRepo):
    """
    ORM-реализация репозитория для управления предметами в инвентаре.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.dto_adapter: TypeAdapter[InventoryItemDTO] = TypeAdapter(InventoryItemDTO)
        log.debug(f"InventoryRepo | status=initialized session={session}")

    async def create_item(
        self,
        character_id: int,
        item_type: str,
        subtype: str,
        rarity: str,
        item_data: dict[str, Any],
        location: str = "inventory",
        quantity: int = 1,
        equipped_slot: str | None = None,
    ) -> int:
        log.debug(f"InventoryRepo | action=create_item char_id={character_id} type='{item_type}' subtype='{subtype}'")
        new_inv_item = InventoryItem(
            character_id=character_id,
            item_type=item_type,
            subtype=subtype,
            rarity=rarity,
            location=location,
            item_data=item_data,
            quantity=quantity,
            equipped_slot=equipped_slot,
        )

        try:
            self.session.add(new_inv_item)
            await self.session.flush()
            log.info(
                f"InventoryRepo | action=create_item status=success item_id={new_inv_item.id} char_id={character_id}"
            )
            return new_inv_item.id
        except SQLAlchemyError:
            log.exception(f"InventoryRepo | action=create_item status=failed char_id={character_id}")
            raise

    async def get_system_item_for_reuse(
        self, item_type: str, rarity: str, subtype: str | None = None
    ) -> InventoryItemDTO | None:
        log.debug(
            f"InventoryRepo | action=get_system_item_for_reuse type='{item_type}' rarity='{rarity}' subtype='{subtype}'"
        )
        query = select(InventoryItem).where(
            InventoryItem.character_id == settings.system_char_id,
            InventoryItem.item_type == item_type,
            InventoryItem.rarity == rarity,
        )

        if subtype:
            query = query.where(InventoryItem.subtype == subtype)

        query = query.order_by(func.random()).limit(1)

        try:
            result = await self.session.execute(query)
            item = result.scalar_one_or_none()

            if item:
                log.info(f"InventoryRepo | action=get_system_item_for_reuse status=found item_id={item.id}")
                return self._to_dto(item)

            log.debug(
                "InventoryRepo | action=get_system_item_for_reuse status=not_found reason='No system item for reuse'"
            )
            return None
        except SQLAlchemyError:
            log.exception(
                f"InventoryRepo | action=get_system_item_for_reuse status=failed type='{item_type}' rarity='{rarity}'"
            )
            raise

    async def transfer_item(self, inventory_id: int, new_owner_id: int, new_location: str = "inventory") -> bool:
        log.debug(
            f"InventoryRepo | action=transfer_item item_id={inventory_id} new_owner={new_owner_id} new_loc='{new_location}'"
        )
        stmt = (
            update(InventoryItem)
            .where(InventoryItem.id == inventory_id)
            .values(character_id=new_owner_id, location=new_location)
        )
        try:
            await self.session.execute(stmt)
            log.info(
                f"InventoryRepo | action=transfer_item status=success item_id={inventory_id} new_owner={new_owner_id}"
            )
            return True
        except SQLAlchemyError:
            log.exception(f"InventoryRepo | action=transfer_item status=failed item_id={inventory_id}")
            return False

    async def get_all_items(self, character_id: int) -> list[InventoryItemDTO]:
        log.debug(f"InventoryRepo | action=get_all_items char_id={character_id}")
        stmt = select(InventoryItem).where(InventoryItem.character_id == character_id)
        try:
            result = await self.session.execute(stmt)
            items = result.scalars().all()
            log.debug(f"InventoryRepo | action=get_all_items status=found count={len(items)} char_id={character_id}")
            return [self._to_dto(item) for item in items]
        except SQLAlchemyError:
            log.exception(f"InventoryRepo | action=get_all_items status=failed char_id={character_id}")
            raise

    async def get_items_by_location(self, character_id: int, location: str) -> list[InventoryItemDTO]:
        log.debug(f"InventoryRepo | action=get_items_by_location char_id={character_id} location='{location}'")
        stmt = select(InventoryItem).where(
            InventoryItem.character_id == character_id, InventoryItem.location == location
        )
        try:
            result = await self.session.execute(stmt)
            items = result.scalars().all()
            log.debug(
                f"InventoryRepo | action=get_items_by_location status=found count={len(items)} char_id={character_id} location='{location}'"
            )
            return [self._to_dto(item) for item in items]
        except SQLAlchemyError:
            log.exception(
                f"InventoryRepo | action=get_items_by_location status=failed char_id={character_id} location='{location}'"
            )
            raise

    async def get_items_by_location_batch(
        self, character_ids: list[int], location: str
    ) -> dict[int, list[InventoryItemDTO]]:
        log.debug(
            f"InventoryRepo | action=get_items_by_location_batch count={len(character_ids)} location='{location}'"
        )
        if not character_ids:
            return {}
        stmt = select(InventoryItem).where(
            InventoryItem.character_id.in_(character_ids), InventoryItem.location == location
        )
        try:
            result = await self.session.execute(stmt)
            items = result.scalars().all()

            # Группируем по character_id
            grouped_items = defaultdict(list)
            for item in items:
                grouped_items[item.character_id].append(self._to_dto(item))

            return dict(grouped_items)
        except SQLAlchemyError:
            log.exception("InventoryRepo | action=get_items_by_location_batch status=failed")
            raise

    async def get_equipped_items(self, character_id: int) -> list[InventoryItemDTO]:
        return await self.get_items_by_location(character_id, "equipped")

    async def get_item_by_id(self, inventory_id: int) -> InventoryItemDTO | None:
        log.debug(f"InventoryRepo | action=get_item_by_id item_id={inventory_id}")
        stmt = select(InventoryItem).where(InventoryItem.id == inventory_id)
        try:
            result = await self.session.execute(stmt)
            item = result.scalar_one_or_none()
            if item:
                log.debug(f"InventoryRepo | action=get_item_by_id status=found item_id={inventory_id}")
                return self._to_dto(item)
            log.debug(f"InventoryRepo | action=get_item_by_id status=not_found item_id={inventory_id}")
            return None
        except SQLAlchemyError:
            log.exception(f"InventoryRepo | action=get_item_by_id status=failed item_id={inventory_id}")
            raise

    async def move_item(self, inventory_id: int, new_location: str) -> bool:
        log.debug(f"InventoryRepo | action=move_item item_id={inventory_id} new_location='{new_location}'")
        stmt = update(InventoryItem).where(InventoryItem.id == inventory_id).values(location=new_location)
        try:
            await self.session.execute(stmt)
            log.info(
                f"InventoryRepo | action=move_item status=success item_id={inventory_id} new_location='{new_location}'"
            )
            return True
        except SQLAlchemyError:
            log.exception(f"InventoryRepo | action=move_item status=failed item_id={inventory_id}")
            return False

    async def delete_item(self, inventory_id: int) -> bool:
        log.debug(f"InventoryRepo | action=delete_item item_id={inventory_id}")
        stmt = delete(InventoryItem).where(InventoryItem.id == inventory_id)
        try:
            await self.session.execute(stmt)
            log.info(f"InventoryRepo | action=delete_item status=success item_id={inventory_id}")
            return True
        except SQLAlchemyError:
            log.exception(f"InventoryRepo | action=delete_item status=failed item_id={inventory_id}")
            return False

    async def update_item_data(self, inventory_id: int, new_data: dict[str, Any]) -> bool:
        log.debug(f"InventoryRepo | action=update_item_data item_id={inventory_id}")
        stmt = update(InventoryItem).where(InventoryItem.id == inventory_id).values(item_data=new_data)
        try:
            await self.session.execute(stmt)
            log.info(f"InventoryRepo | action=update_item_data status=success item_id={inventory_id}")
            return True
        except SQLAlchemyError:
            log.exception(f"InventoryRepo | action=update_item_data status=failed item_id={inventory_id}")
            return False

    async def update_fields(self, inventory_id: int, update_data: dict[str, Any]) -> bool:
        log.debug(f"InventoryRepo | action=update_fields item_id={inventory_id}")
        stmt = update(InventoryItem).where(InventoryItem.id == inventory_id).values(**update_data)
        try:
            await self.session.execute(stmt)
            log.info(f"InventoryRepo | action=update_fields status=success item_id={inventory_id}")
            return True
        except SQLAlchemyError:
            log.exception(f"InventoryRepo | action=update_fields status=failed item_id={inventory_id}")
            return False

    def _to_dto(self, orm_item: InventoryItem) -> InventoryItemDTO:
        dto_dict = {
            "inventory_id": orm_item.id,
            "character_id": orm_item.character_id,
            "location": orm_item.location,
            "item_type": orm_item.item_type,
            "subtype": orm_item.subtype,
            "rarity": orm_item.rarity,
            "data": orm_item.item_data,
            "quantity": orm_item.quantity,
        }
        return self.dto_adapter.validate_python(dto_dict)
