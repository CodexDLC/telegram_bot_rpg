# database/repositories/ORM/skill_repo.py
import logging
from typing import List, Dict, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
# ИСПРАВЛЕНО: Импортируем диалект SQLite
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.resources.game_data.skill_library import SKILL_RECIPES
from app.resources.schemas_dto.skill import SkillRateDTO, SkillProgressDTO
from database.db_contract.i_skill_repo import ISkillRateRepo, ISkillProgressRepo
from database.model_orm.skill import SkillProgressState, CharacterSkillRate, CharacterSkillProgress

log = logging.getLogger(__name__)


class SkillRateRepo(ISkillRateRepo):
    """ORM-реализация репозитория для ставок развития навыков (БСО)."""

    def __init__(self, session: AsyncSession):
        self.session = session
        log.debug(f"Инициализирован {self.__class__.__name__} с сессией: {session}")

    async def upsert_skill_rates(self, rates_data: List[Dict[str, any]]) -> None:
        """Атомарно (через UPSERT) обновляет ставки БСО для персонажа."""
        if not rates_data:
            log.warning("Вызван upsert_skill_rates с пустым списком данных.")
            return

        char_id = rates_data[0].get('character_id')
        log.debug(f"Запрос на UPSERT {len(rates_data)} ставок БСО для character_id={char_id}")

        # ИСПРАВЛЕНО: Используем `sqlite_insert` вместо `pg_insert`
        stmt = sqlite_insert(CharacterSkillRate).values(rates_data)

        # ИСПРАВЛЕНО: Используем синтаксис on_conflict_do_update для SQLite
        stmt = stmt.on_conflict_do_update(
            index_elements=[CharacterSkillRate.character_id, CharacterSkillRate.skill_key],
            set_={"xp_per_tick": stmt.excluded.xp_per_tick}
        )
        try:
            await self.session.execute(stmt)
            log.debug(f"Ставки БСО для character_id={char_id} успешно обновлены.")
        except SQLAlchemyError as e:
            log.exception(f"Ошибка SQLAlchemy при UPSERT ставок БСО для character_id={char_id}: {e}")
            raise

    async def get_all_skill_rates(self, character_id: int, **kwargs) -> List[SkillRateDTO]:
        """Возвращает все рассчитанные ставки БСО для персонажа."""
        log.debug(f"Запрос на получение всех ставок БСО для character_id={character_id}")
        stmt = select(CharacterSkillRate).where(CharacterSkillRate.character_id == character_id)
        try:
            result = await self.session.scalars(stmt)
            orm_rates_list = result.all()
            log.debug(f"Найдено {len(orm_rates_list)} ставок БСО для character_id={character_id}.")
            return [SkillRateDTO.model_validate(orm_rate) for orm_rate in orm_rates_list]
        except SQLAlchemyError as e:
            log.exception(f"Ошибка SQLAlchemy при получении ставок БСО для character_id={character_id}: {e}")
            raise


class SkillProgressRepo(ISkillProgressRepo):
    """ORM-реализация репозитория для прогресса навыков персонажа."""

    def __init__(self, session: AsyncSession):
        self.session = session
        log.debug(f"Инициализирован {self.__class__.__name__} с сессией: {session}")

    async def initialize_all_base_skills(self, character_id: int) -> None:
        """Создает записи для всех базовых навыков для нового персонажа."""
        log.debug(f"Запрос на инициализацию базовых навыков для character_id={character_id}")
        base_skills = [
            {"character_id": character_id, "skill_key": key, "total_xp": 0}
            for key, recipe in SKILL_RECIPES.items()
            if recipe.get("prerequisite_skill") is None
        ]
        if not base_skills:
            log.warning("Не найдено базовых навыков для инициализации.")
            return

        # ИСПРАВЛЕНО: Используем `sqlite_insert` и `on_conflict_do_nothing` для SQLite
        stmt = sqlite_insert(CharacterSkillProgress).values(base_skills)
        stmt = stmt.on_conflict_do_nothing(
            index_elements=[CharacterSkillProgress.character_id, CharacterSkillProgress.skill_key]
        )
        try:
            await self.session.execute(stmt)
            log.info(f"Инициализировано {len(base_skills)} базовых навыков для character_id={character_id}.")
        except SQLAlchemyError as e:
            log.exception(f"Ошибка SQLAlchemy при инициализации навыков для character_id={character_id}: {e}")
            raise

    async def add_skill_xp(self, character_id: int, skill_key: str, xp_to_add: int) -> Optional[SkillProgressDTO]:
        """Атомарно добавляет опыт к навыку и возвращает обновленный прогресс."""
        log.debug(f"Запрос на добавление {xp_to_add} XP к навыку '{skill_key}' для character_id={character_id}")

        # ИСПРАВЛЕНО: Разделяем на 2 шага: UPDATE, затем SELECT.

        # Шаг 1: Выполняем UPDATE
        stmt_update = (
            update(CharacterSkillProgress)
            .where(
                CharacterSkillProgress.character_id == character_id,
                CharacterSkillProgress.skill_key == skill_key
            )
            .values(total_xp=CharacterSkillProgress.total_xp + xp_to_add)
        )

        # Шаг 2: Готовим SELECT для получения обновленных данных
        stmt_select = (
            select(CharacterSkillProgress)
            .where(
                CharacterSkillProgress.character_id == character_id,
                CharacterSkillProgress.skill_key == skill_key
            )
        )

        try:
            # Выполняем Шаг 1
            await self.session.execute(stmt_update)
            log.debug(f"Опыт для навыка '{skill_key}' у character_id={character_id} обновлен (шаг 1/2).")

            # Выполняем Шаг 2
            result = await self.session.execute(stmt_select)
            orm_progress = result.scalar_one_or_none()

            if orm_progress:
                log.debug(f"Обновленный DTO для '{skill_key}' (character_id={character_id}) успешно получен (шаг 2/2).")
                return SkillProgressDTO.model_validate(orm_progress)

            log.warning(
                f"Не удалось добавить опыт (или получить DTO): навык '{skill_key}' не найден для character_id={character_id} *после* обновления.")
            return None

        except SQLAlchemyError as e:
            log.exception(
                f"Ошибка SQLAlchemy при добавлении опыта к навыку '{skill_key}' для character_id={character_id}: {e}")
            raise

    async def update_skill_state(self, character_id: int, skill_key: str, state: SkillProgressState) -> None:
        """Обновляет состояние развития навыка (PLUS/PAUSE/MINUS)."""
        log.debug(
            f"Запрос на обновление состояния навыка '{skill_key}' на '{state.name}' для character_id={character_id}")
        stmt = (
            update(CharacterSkillProgress)
            .where(
                CharacterSkillProgress.character_id == character_id,
                CharacterSkillProgress.skill_key == skill_key
            )
            .values(progress_state=state)
        )
        try:
            await self.session.execute(stmt)
            log.debug(f"Состояние навыка '{skill_key}' для character_id={character_id} обновлено.")
        except SQLAlchemyError as e:
            log.exception(
                f"Ошибка SQLAlchemy при обновлении состояния навыка '{skill_key}' для character_id={character_id}: {e}")
            raise

    async def update_skill_unlocked_state(self, character_id: int, skill_key_list: list[str], state: bool):

        """Обновляет состояние unlocked поля  """
        log.debug(
            f"Запрос на отрытия навыков из списка '{skill_key_list}' на '{state}' для character_id={character_id}"
        )
        stmt = (update(CharacterSkillProgress)
                .where(CharacterSkillProgress.character_id == character_id,
                       CharacterSkillProgress.skill_key.in_(skill_key_list))
                .values(is_unlocked=state))

        try:
            await self.session.execute(stmt)
            log.debug(f"Состояние навыков из списка '{skill_key_list}' для character_id={character_id} обновлено.")
        except SQLAlchemyError as e:
            log.exception(
                f"Ошибка SQLAlchemy при обновлении состояния навыков '{skill_key_list}' для character_id={character_id}: {e}")
            raise


    async def get_all_skills_progress(self, character_id: int, **kwargs) -> List[SkillProgressDTO]:
        """Возвращает прогресс всех навыков персонажа."""
        log.debug(f"Запрос на получение прогресса всех навыков для character_id={character_id}")
        stmt = select(CharacterSkillProgress).where(CharacterSkillProgress.character_id == character_id)
        try:
            result = await self.session.scalars(stmt)
            orm_progress_list = result.all()
            log.debug(f"Найдено {len(orm_progress_list)} записей о прогрессе навыков для character_id={character_id}.")
            return [SkillProgressDTO.model_validate(orm_progress) for orm_progress in orm_progress_list]
        except SQLAlchemyError as e:
            log.exception(f"Ошибка SQLAlchemy при получении прогресса навыков для character_id={character_id}: {e}")
            raise