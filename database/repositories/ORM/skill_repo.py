# database/repositories/ORM/skill_repo.py
import logging
from typing import List, Dict, Optional


from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, insert
from sqlalchemy.dialects.sqlite import insert

from app.resources.game_data.skill_library import SKILL_RECIPES
from app.resources.schemas_dto.skill import SkillRateDTO, SkillProgressDTO
from database.db_contract.i_skill_repo import ISkillRateRepo, ISkillProgressRepo
from database.model_orm.skill import SkillProgressState, CharacterSkillRate, CharacterSkillProgress

log = logging.getLogger(__name__)

class SkillRateRepo(ISkillRateRepo):
    """
    Контракт для C.R.U.D. таблицы 'character_skill_rates' (БСО)
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert_skill_rates(self, rates_data: List[Dict[str, any]]) -> None:
        """
        Атомарно (через UPSERT) обновляет ВСЕ ставки БСО.
        (Это исправленная версия)
        """
        if not rates_data:
            log.warning("Вызван upsert_skill_rates с пустым словарем БСО.")
            return

        # 1. Создаем запрос UPSERT (ON CONFLICT DO UPDATE)
        stmt = insert(CharacterSkillRate).values(rates_data)

        # 2. VVVV ВОТ ИСПРАВЛЕНИЕ VVVV
        stmt = stmt.on_conflict_do_update(
            index_elements=["character_id", "skill_key"],
            set_={"xp_per_tick": stmt.excluded.xp_per_tick}
        )

        await self.session.execute(stmt)

    async def get_all_skill_rates(self, character_id: int, **kwargs) -> List[SkillRateDTO]:
        """
        Возвращает ВСЕ рассчитанные ставки БСО для персонажа.
        """
        stmt = select(CharacterSkillRate).where(CharacterSkillRate.character_id == character_id)

        result = await self.session.scalars(stmt)
        orm_rates_list = result.all()

        if orm_rates_list:
            log.debug(f"БСО получены: {orm_rates_list}")
            return [SkillRateDTO.model_validate(orm_rate) for orm_rate in orm_rates_list]
        return []




class SkillProgressRepo(ISkillProgressRepo):
    """
    Контракт для C.R.U.D. таблицы 'character_skill_progress'
    """
    def __init__(self, session: AsyncSession):
        self.session = session

    async def initialize_all_base_skills(self, character_id: int) -> None:
        """
        (ТВОЙ НОВЫЙ МЕТОД)
        Создает (INSERT) все БАЗОВЫЕ навыки (Уровень 1) для
        персонажа со значением total_xp = 0.
        (Использует self.session)
        """
        data = SKILL_RECIPES

        # 1. Создаем запрос INSERT
        stmt = insert(CharacterSkillProgress).values(
            [{"character_id": character_id, "skill_key": skill_key, "total_xp": 0} for skill_key in data.keys()
             if data[skill_key].get("prerequisite_skill") is None]
            )

        # 2. отправляем запрос
        stmt = stmt.on_conflict_do_nothing(
            index_elements=["character_id", "skill_key"]
            )

        await self.session.execute(stmt)


    async def add_skill_xp(self, character_id: int, skill_key: str, xp_to_add: int) ->  Optional[SkillProgressDTO]:
        """
        Атомарно ДОБАВЛЯЕТ опыт к 'total_xp'.
        Это наш главный метод прокачки.
        (UPDATE character_skill_progress SET total_xp = total_xp + ? WHERE ...)
        Возвращает DTO с *рассчитанным* новым уровнем.
        """
        stmt = update(CharacterSkillProgress).where(
            CharacterSkillProgress.character_id == character_id,
            CharacterSkillProgress.skill_key == skill_key
        ).values(
            total_xp=CharacterSkillProgress.total_xp + xp_to_add
        ).returning(CharacterSkillProgress)

        result = await self.session.execute(stmt)
        orm_progress = result.scalar_one_or_none()
        if orm_progress:
            return SkillProgressDTO.model_validate(orm_progress)
        return None


    async def update_skill_state(self, character_id: int, skill_key: str, state: SkillProgressState) -> None:
        """
        Обновляет ТОЛЬКО состояние (PLUS/PAUSE/MINUS).
        (Твой 'update_skill_progress' был нужен, но только для этого)
        """

        stmt = update(CharacterSkillProgress).where(
            CharacterSkillProgress.character_id==character_id,
            CharacterSkillProgress.skill_key==skill_key).values(progress_state=state)

        await self.session.execute(stmt)


    async def get_all_skills_progress(self, character_id: int, **kwargs) -> List[SkillProgressDTO]:

        """
        Возвращает прогресс ВСЕХ навыков персонажа.
        """
        stmt = select(CharacterSkillProgress).where(CharacterSkillProgress.character_id == character_id)

        result = await self.session.scalars(stmt)
        orm_progress_list = result.all()

        if orm_progress_list:
            log.debug(f"Прогресс получен: {orm_progress_list}")
            return [SkillProgressDTO.model_validate(orm_progress) for orm_progress in orm_progress_list]
        return []


