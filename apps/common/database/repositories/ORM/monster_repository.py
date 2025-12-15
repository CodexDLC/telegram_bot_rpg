from uuid import UUID

from loguru import logger as log
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from apps.common.database.db_contract.i_monster_repository import IMonsterRepository
from apps.common.database.model_orm.monster import GeneratedClanORM, GeneratedMonsterORM
from apps.common.schemas_dto.monster_dto import GeneratedMonsterDTO


class MonsterRepository(IMonsterRepository):
    """
    Репозиторий для работы с ORM-моделями монстров и кланов.
    """

    def __init__(self, session: AsyncSession):
        """
        Инициализирует репозиторий.

        Args:
            session: Сессия БД.
        """
        self.session = session
        log.debug("MonsterRepositoryInit")

    async def get_clan_by_unique_hash(self, unique_hash: str) -> GeneratedClanORM | None:
        """
        Находит клан по его уникальному хешу.

        Используется для предотвращения дублирования кланов при генерации.

        Args:
            unique_hash: Уникальный хеш, идентифицирующий клан в контексте.

        Returns:
            ORM-объект клана или None, если не найден.
        """
        log.debug(f"GetClanByHash | hash='{unique_hash}'")
        query = (
            select(GeneratedClanORM)
            .where(GeneratedClanORM.unique_hash == unique_hash)
            .options(selectinload(GeneratedClanORM.members))
        )
        result = await self.session.execute(query)
        return result.scalars().first()

    async def create_clan_with_members(
        self, clan_orm: GeneratedClanORM, monsters_orm: list[GeneratedMonsterORM]
    ) -> GeneratedClanORM:
        """
        Атомарно сохраняет клан и его членов в одной транзакции.

        Args:
            clan_orm: ORM-объект клана.
            monsters_orm: Список ORM-объектов монстров.

        Returns:
            Сохраненный ORM-объект клана.
        """
        log.info(f"CreateClan | clan_id='{clan_orm.id}' members_count={len(monsters_orm)}")
        clan_orm.members.extend(monsters_orm)
        self.session.add_all([clan_orm] + monsters_orm)
        await self.session.flush([clan_orm])
        return clan_orm

    async def get_all_clans_by_context(self, context_hash: str) -> list[GeneratedClanORM]:
        """
        Получает все кланы, соответствующие хешу контекста (например, все кланы в одной зоне).
        """
        log.debug(f"GetClansByContext | context_hash='{context_hash}'")
        query = (
            select(GeneratedClanORM)
            .where(GeneratedClanORM.context_hash == context_hash)
            .options(selectinload(GeneratedClanORM.members))
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_monster_by_id(self, monster_id: UUID | str) -> GeneratedMonsterORM | None:
        """
        Находит монстра по его UUID.
        """
        log.debug(f"GetMonsterById | monster_id='{monster_id}'")
        real_uuid: UUID
        if isinstance(monster_id, str):
            try:
                real_uuid = UUID(monster_id)
            except ValueError:
                log.warning(f"GetMonsterByIdFail | reason=invalid_uuid monster_id='{monster_id}'")
                return None
        else:
            real_uuid = monster_id

        query = (
            select(GeneratedMonsterORM)
            .where(GeneratedMonsterORM.id == real_uuid)
            .options(selectinload(GeneratedMonsterORM.clan))
        )
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_monster_for_combat(self, monster_id: UUID | str) -> GeneratedMonsterDTO | None:
        """
        Загружает монстра и преобразует его в DTO для боевой системы.
        """
        log.debug(f"GetMonsterForCombat | monster_id='{monster_id}'")
        monster_orm = await self.get_monster_by_id(monster_id)
        if not monster_orm:
            return None
        return GeneratedMonsterDTO.model_validate(monster_orm)

    async def get_all_clans(self) -> list[GeneratedClanORM]:
        """Загружает ВСЕ существующие кланы с их участниками."""
        log.debug("GetAllClans")
        query = select(GeneratedClanORM).options(selectinload(GeneratedClanORM.members))
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_clans_by_zone(self, zone_id: str) -> list[GeneratedClanORM]:
        """Загружает все кланы в указанной зоне."""
        log.debug(f"GetClansByZone | zone_id='{zone_id}'")
        query = select(GeneratedClanORM).where(GeneratedClanORM.zone_id == zone_id)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_monsters_by_role_and_threat(
        self, role: str, min_threat: int, max_threat: int, limit: int = 5
    ) -> list[GeneratedMonsterORM]:
        """
        Ищет случайных монстров по роли и уровню угрозы.
        """
        log.debug(f"GetMonstersByRole | role='{role}' min_threat={min_threat} max_threat={max_threat} limit={limit}")
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
