from typing import Any

from loguru import logger as log
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.database.db_contract.i_skill_repo import ISkillProgressRepo, ISkillRateRepo
from apps.common.database.model_orm.skill import CharacterSkillProgress, CharacterSkillRate, SkillProgressState
from apps.common.schemas_dto.skill import SkillProgressDTO, SkillRateDTO
from apps.game_core.resources.game_data.skill_library import SKILL_RECIPES


class SkillRateRepo(ISkillRateRepo):
    """
    ORM-реализация репозитория для ставок развития навыков (БСО).

    Предоставляет методы для массового создания/обновления и получения
    ставок опыта для навыков персонажа.
    """

    def __init__(self, session: AsyncSession):
        """
        Инициализирует SkillRateRepo.

        Args:
            session: Асинхронная сессия SQLAlchemy.
        """
        self.session = session
        log.debug(f"SkillRateRepo | status=initialized session={session}")

    async def upsert_skill_rates(self, rates_data: list[dict[str, Any]]) -> None:
        """
        Массово создает или обновляет ставки опыта для навыков персонажа.

        Использует Postgres UPSERT для атомарной операции.

        Args:
            rates_data: Список словарей с данными для UPSERT.
        """
        if not rates_data:
            log.warning("SkillRateRepo | action=upsert_skill_rates reason='Empty data list'")
            return

        char_id = rates_data[0].get("character_id")
        log.debug(f"SkillRateRepo | action=upsert_skill_rates count={len(rates_data)} char_id={char_id}")

        stmt = pg_insert(CharacterSkillRate).values(rates_data)
        stmt = stmt.on_conflict_do_update(
            index_elements=[CharacterSkillRate.character_id, CharacterSkillRate.skill_key],
            set_={"xp_per_tick": stmt.excluded.xp_per_tick},
        )
        try:
            await self.session.execute(stmt)
            log.info(f"SkillRateRepo | action=upsert_skill_rates status=success char_id={char_id}")
        except SQLAlchemyError:
            log.exception(f"SkillRateRepo | action=upsert_skill_rates status=failed char_id={char_id}")
            raise

    async def get_all_skill_rates(self, character_id: int) -> list[SkillRateDTO]:
        """
        Возвращает все рассчитанные ставки опыта для навыков одного персонажа.

        Args:
            character_id: Идентификатор персонажа.

        Returns:
            Список DTO `SkillRateDTO` со ставками навыков.
        """
        log.debug(f"SkillRateRepo | action=get_all_skill_rates char_id={character_id}")
        stmt = select(CharacterSkillRate).where(CharacterSkillRate.character_id == character_id)
        try:
            result = await self.session.scalars(stmt)
            orm_rates_list = result.all()
            log.debug(
                f"SkillRateRepo | action=get_all_skill_rates status=found count={len(orm_rates_list)} char_id={character_id}"
            )
            return [SkillRateDTO.model_validate(orm_rate) for orm_rate in orm_rates_list]
        except SQLAlchemyError:
            log.exception(f"SkillRateRepo | action=get_all_skill_rates status=failed char_id={character_id}")
            raise


class SkillProgressRepo(ISkillProgressRepo):
    """
    ORM-реализация репозитория для прогресса навыков персонажа.

    Предоставляет методы для инициализации, добавления опыта,
    обновления состояния и получения прогресса навыков.
    """

    def __init__(self, session: AsyncSession):
        """
        Инициализирует SkillProgressRepo.

        Args:
            session: Асинхронная сессия SQLAlchemy.
        """
        self.session = session
        log.debug(f"SkillProgressRepo | status=initialized session={session}")

    async def initialize_all_base_skills(self, character_id: int) -> None:
        """
        Инициализирует записи для всех базовых навыков для нового персонажа.

        Args:
            character_id: Идентификатор персонажа, для которого инициализируются навыки.
        """
        log.debug(f"SkillProgressRepo | action=initialize_all_base_skills char_id={character_id}")
        base_skills = [
            {"character_id": character_id, "skill_key": key, "total_xp": 0}
            for key, recipe in SKILL_RECIPES.items()
            if isinstance(recipe, dict) and recipe.get("prerequisite_skill") is None
        ]
        if not base_skills:
            log.warning(
                "SkillProgressRepo | action=initialize_all_base_skills reason='No base skills found for initialization'"
            )
            return

        stmt = pg_insert(CharacterSkillProgress).values(base_skills)
        stmt = stmt.on_conflict_do_nothing(
            index_elements=[CharacterSkillProgress.character_id, CharacterSkillProgress.skill_key]
        )
        try:
            await self.session.execute(stmt)
            log.info(
                f"SkillProgressRepo | action=initialize_all_base_skills status=success count={len(base_skills)} char_id={character_id}"
            )
        except SQLAlchemyError:
            log.exception(f"SkillProgressRepo | action=initialize_all_base_skills status=failed char_id={character_id}")
            raise

    async def add_skill_xp(self, character_id: int, skill_key: str, xp_to_add: int) -> SkillProgressDTO | None:
        """
        Атомарно добавляет опыт к указанному навыку персонажа и возвращает обновленный прогресс.

        Args:
            character_id: Идентификатор персонажа.
            skill_key: Ключ навыка.
            xp_to_add: Количество опыта для добавления.

        Returns:
            Обновленный DTO `SkillProgressDTO` прогресса навыка,
            если запись найдена и обновлена. Иначе - None.
        """
        log.debug(
            f"SkillProgressRepo | action=add_skill_xp char_id={character_id} skill='{skill_key}' xp_to_add={xp_to_add}"
        )

        stmt_update = (
            update(CharacterSkillProgress)
            .where(CharacterSkillProgress.character_id == character_id, CharacterSkillProgress.skill_key == skill_key)
            .values(total_xp=CharacterSkillProgress.total_xp + xp_to_add)
        )
        stmt_select = select(CharacterSkillProgress).where(
            CharacterSkillProgress.character_id == character_id, CharacterSkillProgress.skill_key == skill_key
        )

        try:
            await self.session.execute(stmt_update)
            result = await self.session.execute(stmt_select)
            orm_progress = result.scalar_one_or_none()

            if orm_progress:
                log.debug(
                    f"SkillProgressRepo | action=add_skill_xp status=success char_id={character_id} skill='{skill_key}' new_xp={orm_progress.total_xp}"
                )
                return SkillProgressDTO.model_validate(orm_progress)

            log.warning(
                f"SkillProgressRepo | action=add_skill_xp status=failed reason='Skill not found after update' char_id={character_id} skill='{skill_key}'"
            )
            return None

        except SQLAlchemyError:
            log.exception(
                f"SkillProgressRepo | action=add_skill_xp status=failed char_id={character_id} skill='{skill_key}'"
            )
            raise

    async def update_skill_state(self, character_id: int, skill_key: str, state: SkillProgressState) -> None:
        """
        Обновляет состояние развития навыка (PLUS, PAUSE, MINUS).

        Args:
            character_id: Идентификатор персонажа.
            skill_key: Ключ навыка.
            state: Новое состояние навыка (Enum `SkillProgressState`).
        """
        log.debug(
            f"SkillProgressRepo | action=update_skill_state char_id={character_id} skill='{skill_key}' new_state='{state.name}'"
        )
        stmt = (
            update(CharacterSkillProgress)
            .where(CharacterSkillProgress.character_id == character_id, CharacterSkillProgress.skill_key == skill_key)
            .values(progress_state=state)
        )
        try:
            await self.session.execute(stmt)
            log.info(
                f"SkillProgressRepo | action=update_skill_state status=success char_id={character_id} skill='{skill_key}'"
            )
        except SQLAlchemyError:
            log.exception(
                f"SkillProgressRepo | action=update_skill_state status=failed char_id={character_id} skill='{skill_key}'"
            )
            raise

    async def update_skill_unlocked_state(self, character_id: int, skill_key_list: list[str], state: bool) -> None:
        """
        Массово обновляет статус `is_unlocked` для списка навыков персонажа.

        Args:
            character_id: Идентификатор персонажа, чьи навыки обновляются.
            skill_key_list: Список строковых ключей навыков.
            state: Новое состояние для `is_unlocked` (True - разблокирован, False - заблокирован).
        """
        log.debug(
            f"SkillProgressRepo | action=update_skill_unlocked_state char_id={character_id} skills={skill_key_list} new_state={state}"
        )
        stmt = (
            update(CharacterSkillProgress)
            .where(
                CharacterSkillProgress.character_id == character_id,
                CharacterSkillProgress.skill_key.in_(skill_key_list),
            )
            .values(is_unlocked=state)
        )

        try:
            await self.session.execute(stmt)
            log.info(
                f"SkillProgressRepo | action=update_skill_unlocked_state status=success char_id={character_id} skills={skill_key_list}"
            )
        except SQLAlchemyError:
            log.exception(
                f"SkillProgressRepo | action=update_skill_unlocked_state status=failed char_id={character_id} skills={skill_key_list}"
            )
            raise

    async def get_all_skills_progress(self, character_id: int) -> list[SkillProgressDTO]:
        """
        Возвращает прогресс всех навыков для одного персонажа.

        Args:
            character_id: Идентификатор персонажа.

        Returns:
            Список DTO `SkillProgressDTO` с прогрессом всех навыков.
        """
        log.debug(f"SkillProgressRepo | action=get_all_skills_progress char_id={character_id}")
        stmt = select(CharacterSkillProgress).where(CharacterSkillProgress.character_id == character_id)
        try:
            result = await self.session.scalars(stmt)
            orm_progress_list = result.all()
            log.debug(
                f"SkillProgressRepo | action=get_all_skills_progress status=found count={len(orm_progress_list)} char_id={character_id}"
            )
            return [SkillProgressDTO.model_validate(orm_progress) for orm_progress in orm_progress_list]
        except SQLAlchemyError:
            log.exception(f"SkillProgressRepo | action=get_all_skills_progress status=failed char_id={character_id}")
            raise
