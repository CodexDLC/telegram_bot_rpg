from typing import Any

from loguru import logger as log
from sqlalchemy import select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from database.db_contract.i_world_repo import IWorldRepo
from database.model_orm.world import WorldGrid, WorldRegion


class WorldRepoORM(IWorldRepo):
    """
    ORM-реализация репозитория Мира (WorldRepo).
    Работает через SQLAlchemy с таблицами world_regions и world_grid.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    # =========================================================================
    # РЕГИОНЫ (Regions)
    # =========================================================================

    async def upsert_region(self, region_data: WorldRegion) -> None:
        """
        Создает или обновляет запись о Регионе (15x15).
        """
        try:
            # merge - универсальный метод для upsert в ORM
            await self.session.merge(region_data)
            # log.debug(f"WorldRepo | region upserted id={region_data.id}")
        except SQLAlchemyError as e:
            log.error(f"WorldRepo | region upsert failed id={region_data.id} error={e}")
            raise

    async def get_region(self, region_id: str) -> WorldRegion | None:
        """Получает данные региона по ID."""
        stmt = select(WorldRegion).where(WorldRegion.id == region_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    # =========================================================================
    # КЛЕТКИ (Nodes / Grid)
    # =========================================================================

    async def get_node(self, x: int, y: int) -> WorldGrid | None:
        """Получает одну клетку по координатам."""
        stmt = select(WorldGrid).where(WorldGrid.x == x, WorldGrid.y == y)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_or_update_node(
        self,
        x: int,
        y: int,
        sector_id: str,
        is_active: bool = False,
        flags: dict | None = None,
        content: dict | None = None,
        service_key: str | None = None,
    ) -> None:
        """
        Полная запись клетки (UPSERT).
        Используется генератором (Seeding).
        """
        # Используем диалект-специфичный Insert для SQLite (ON CONFLICT DO UPDATE)
        stmt = sqlite_insert(WorldGrid).values(
            x=x,
            y=y,
            sector_id=sector_id,
            is_active=is_active,
            flags=flags or {},
            content=content,
            service_object_key=service_key,
        )

        do_update_stmt = stmt.on_conflict_do_update(
            index_elements=["x", "y"],
            set_={
                "sector_id": stmt.excluded.sector_id,
                "is_active": stmt.excluded.is_active,
                "flags": stmt.excluded.flags,
                "content": stmt.excluded.content,
                "service_object_key": stmt.excluded.service_object_key,
            },
        )

        try:
            await self.session.execute(do_update_stmt)
        except SQLAlchemyError as e:
            log.error(f"WorldRepo | node upsert failed x={x} y={y} error={e}")
            raise

    async def update_flags(self, x: int, y: int, new_flags: dict[str, Any], activate_node: bool = False) -> bool:
        """
        Точечное обновление JSON-поля `flags`.
        Мерджит новые флаги с существующими.
        """
        # 1. Читаем текущие данные (нам нужен старый словарь флагов)
        node = await self.get_node(x, y)
        if not node:
            return False

        # 2. Мерджим словари (Python dict update)
        current_flags = dict(node.flags) if node.flags else {}
        current_flags.update(new_flags)

        # 3. Готовим данные для обновления
        values_to_update: dict[str, Any] = {"flags": current_flags}
        if activate_node:
            values_to_update["is_active"] = True

        # 4. Выполняем Update
        stmt = update(WorldGrid).where(WorldGrid.x == x, WorldGrid.y == y).values(**values_to_update)

        try:
            await self.session.execute(stmt)
            return True
        except SQLAlchemyError as e:
            log.error(f"WorldRepo | update_flags failed x={x} y={y} error={e}")
            return False

    async def update_content(self, x: int, y: int, new_content: dict[str, Any]) -> bool:
        """
        Точечное обновление JSON-поля `content`.
        Мерджит (или перезаписывает) поля контента.
        """
        node = await self.get_node(x, y)
        if not node:
            return False

        # Мерджим контент (например, обновляем описание, сохраняя старые теги, если они там были)
        # Хотя обычно для контента мы перезаписываем его целиком из ЛЛМ,
        # но безопаснее сначала прочитать.
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
        """
        Возвращает список ВСЕХ активных клеток.
        """
        stmt = select(WorldGrid).where(WorldGrid.is_active == True)  # noqa: E712
        result = await self.session.execute(stmt)
        nodes = result.scalars().all()
        # log.debug(f"WorldRepo | fetched {len(nodes)} active nodes")
        return list(nodes)
