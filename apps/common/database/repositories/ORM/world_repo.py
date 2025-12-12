from typing import Any

from loguru import logger as log
from sqlalchemy import select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.database.db_contract.i_world_repo import IWorldRepo
from apps.common.database.model_orm.world import WorldGrid, WorldRegion, WorldZone


class WorldRepoORM(IWorldRepo):
    """
    ORM-реализация репозитория Мира (WorldRepo).
    Работает через SQLAlchemy с таблицами world_regions, world_zones и world_grid.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    # =========================================================================
    # 1. РЕГИОНЫ (Regions 15x15)
    # =========================================================================

    async def upsert_region(self, region_data: WorldRegion) -> None:
        try:
            await self.session.merge(region_data)
        except SQLAlchemyError as e:
            log.error(f"WorldRepo | region upsert failed id={region_data.id} error={e}")
            raise

    async def get_region(self, region_id: str) -> WorldRegion | None:
        stmt = select(WorldRegion).where(WorldRegion.id == region_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    # =========================================================================
    # 2. ЗОНЫ (Zones 5x5) - NEW
    # =========================================================================

    async def upsert_zone(self, zone_data: WorldZone) -> None:
        """
        Создает или обновляет Зону.
        """
        try:
            await self.session.merge(zone_data)
        except SQLAlchemyError as e:
            log.error(f"WorldRepo | zone upsert failed id={zone_data.id} error={e}")
            raise

    async def get_zone(self, zone_id: str) -> WorldZone | None:
        stmt = select(WorldZone).where(WorldZone.id == zone_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_zones_by_region(self, region_id: str) -> list[WorldZone]:
        stmt = select(WorldZone).where(WorldZone.region_id == region_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # =========================================================================
    # 3. КЛЕТКИ (Nodes 1x1)
    # =========================================================================

    async def get_node(self, x: int, y: int) -> WorldGrid | None:
        # Важно: делаем join с Zone, чтобы сразу иметь доступ к region_id и biome_id при чтении
        stmt = select(WorldGrid).where(WorldGrid.x == x, WorldGrid.y == y)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_or_update_node(
        self,
        x: int,
        y: int,
        zone_id: str,
        terrain_type: str,
        is_active: bool = False,
        flags: dict | None = None,
        content: dict | None = None,
        services: list[str] | None = None,
    ) -> None:
        """
        Полная запись клетки (UPSERT).
        """
        if services is None:
            services = []

        stmt = sqlite_insert(WorldGrid).values(
            x=x,
            y=y,
            zone_id=zone_id,
            terrain_type=terrain_type,
            is_active=is_active,
            flags=flags or {},
            content=content,
            services=services,
        )

        do_update_stmt = stmt.on_conflict_do_update(
            index_elements=["x", "y"],
            set_={
                "zone_id": stmt.excluded.zone_id,
                "terrain_type": stmt.excluded.terrain_type,
                "is_active": stmt.excluded.is_active,
                "flags": stmt.excluded.flags,
                "content": stmt.excluded.content,
                "services": stmt.excluded.services,
            },
        )

        try:
            await self.session.execute(do_update_stmt)
        except SQLAlchemyError as e:
            log.error(f"WorldRepo | node upsert failed x={x} y={y} error={e}")
            raise

    async def update_flags(self, x: int, y: int, new_flags: dict[str, Any], activate_node: bool = False) -> bool:
        node = await self.get_node(x, y)
        if not node:
            return False

        current_flags = dict(node.flags) if node.flags else {}
        current_flags.update(new_flags)

        values_to_update: dict[str, Any] = {"flags": current_flags}
        if activate_node:
            values_to_update["is_active"] = True

        stmt = update(WorldGrid).where(WorldGrid.x == x, WorldGrid.y == y).values(**values_to_update)

        try:
            await self.session.execute(stmt)
            return True
        except SQLAlchemyError as e:
            log.error(f"WorldRepo | update_flags failed x={x} y={y} error={e}")
            return False

    async def update_content(self, x: int, y: int, new_content: dict[str, Any]) -> bool:
        node = await self.get_node(x, y)
        if not node:
            return False

        current_content = dict(node.content) if node.content else {}
        current_content.update(new_content)

        stmt = update(WorldGrid).where(WorldGrid.x == x, WorldGrid.y == y).values(content=current_content)

        try:
            await self.session.execute(stmt)
            return True
        except SQLAlchemyError as e:
            log.error(f"WorldRepo | update_content failed x={x} y={y} error={e}")
            return False

    async def get_active_nodes(self) -> list[WorldGrid]:
        # При загрузке активных нод нам часто нужны данные Зоны (biome_id)
        # Поэтому делаем joinedload (оптимизация)
        from sqlalchemy.orm import joinedload

        stmt = select(WorldGrid).options(joinedload(WorldGrid.zone)).where(WorldGrid.is_active == True)  # noqa: E712
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_nodes_in_rect(self, x: int, y: int, width: int, height: int) -> list[WorldGrid]:
        stmt = select(WorldGrid).where(
            WorldGrid.x >= x, WorldGrid.x < x + width, WorldGrid.y >= y, WorldGrid.y < y + height
        )
        try:
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            log.error(f"WorldRepo | get_nodes_in_rect failed x={x} y={y} error={e}")
            return []
