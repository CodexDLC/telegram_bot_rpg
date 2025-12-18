# apps/game_core/game_service/monster/encounter_pool_service.py
import random

from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.database.model_orm.monster import GeneratedClanORM
from apps.common.database.repositories.ORM.monster_repository import MonsterRepository
from apps.game_core.game_service.monster.clan_hashing import compute_context_hash, normalize_tags


class EncounterPoolService:
    """
    Сервис для выбора случайной встречи из пула уже сгенерированных кланов.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = MonsterRepository(session)

    async def get_random_encounter(self, tier: int, biome_id: str, raw_tags: list[str]) -> GeneratedClanORM | None:
        """
        Выбирает случайный клан из БД по хешу контекста.
        Возвращает ORM-объект клана.
        """
        normalized_tags = normalize_tags(raw_tags)
        context_hash = compute_context_hash(tier, biome_id, normalized_tags)
        log.debug(f"EncounterPool | Getting clans for hash='{context_hash}'")

        candidate_clans = await self.repo.get_clans_by_context_hash(context_hash)

        if not candidate_clans:
            log.warning(f"EncounterPool | No clans found for hash='{context_hash}'")
            return None

        selected_clan = random.choice(candidate_clans)
        log.debug(f"EncounterPool | Selected clan '{selected_clan.family_id}' (id={selected_clan.id})")

        return selected_clan
