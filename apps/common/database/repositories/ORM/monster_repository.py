# apps/common/database/repositories/ORM/monster_repository.py
from uuid import UUID

from loguru import logger as log
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from apps.common.database.db_contract.i_monster_repository import IMonsterRepository
from apps.common.database.model_orm.monster import GeneratedClanORM, GeneratedMonsterORM
from apps.common.schemas_dto.monster_dto import GeneratedMonsterDTO


class MonsterRepository(IMonsterRepository):
    def __init__(self, session: AsyncSession):
        self.session = session
        log.debug("MonsterRepositoryInit")

    async def get_clan_by_unique_hash(self, unique_hash: str) -> GeneratedClanORM | None:
        query = select(GeneratedClanORM).where(GeneratedClanORM.unique_hash == unique_hash)
        result = await self.session.execute(query)
        return result.scalars().first()

    async def create_clan_with_members(
        self, clan_orm: GeneratedClanORM, monsters_orm: list[GeneratedMonsterORM]
    ) -> GeneratedClanORM:
        clan_orm.members.extend(monsters_orm)
        self.session.add_all([clan_orm] + monsters_orm)
        await self.session.flush([clan_orm])
        return clan_orm

    async def get_clans_by_context_hash(self, context_hash: str) -> list[GeneratedClanORM]:
        # Оставляем старый метод для совместимости (с жадной загрузкой)
        query = (
            select(GeneratedClanORM)
            .where(GeneratedClanORM.context_hash == context_hash)
            .options(selectinload(GeneratedClanORM.members))
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    # --- Новые методы для оптимизированного выбора ---

    async def get_clan_ids_by_context_hash(self, context_hash: str) -> list[UUID]:
        """Возвращает только ID кланов (быстро)."""
        query = select(GeneratedClanORM.id).where(GeneratedClanORM.context_hash == context_hash)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_clan_members(self, clan_id: UUID) -> list[GeneratedMonsterORM]:
        """Возвращает всех монстров конкретного клана."""
        query = select(GeneratedMonsterORM).where(GeneratedMonsterORM.family_id == clan_id)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    # ------------------------------------------------

    async def get_monster_by_id(self, monster_id: UUID | str) -> GeneratedMonsterORM | None:
        try:
            real_uuid = UUID(str(monster_id)) if not isinstance(monster_id, UUID) else monster_id
        except ValueError:
            log.warning(f"GetMonsterByIdFail | reason=invalid_uuid monster_id='{monster_id}'")
            return None

        query = (
            select(GeneratedMonsterORM)
            .where(GeneratedMonsterORM.id == real_uuid)
            .options(selectinload(GeneratedMonsterORM.clan))
        )
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_monster_for_combat(self, monster_id: UUID | str) -> GeneratedMonsterDTO | None:
        monster_orm = await self.get_monster_by_id(monster_id)
        if not monster_orm:
            return None
        return GeneratedMonsterDTO.model_validate(monster_orm)

    async def get_all_clans(self) -> list[GeneratedClanORM]:
        query = select(GeneratedClanORM).options(selectinload(GeneratedClanORM.members))
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_clans_by_zone(self, zone_id: str) -> list[GeneratedClanORM]:
        query = select(GeneratedClanORM).where(GeneratedClanORM.zone_id == zone_id)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_monsters_by_role_and_threat(
        self, role: str, min_threat: int, max_threat: int, limit: int = 5
    ) -> list[GeneratedMonsterORM]:
        query = (
            select(GeneratedMonsterORM)
            .where(
                GeneratedMonsterORM.role == role,
                GeneratedMonsterORM.threat_rating >= min_threat,
                GeneratedMonsterORM.threat_rating <= max_threat,
            )
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())
