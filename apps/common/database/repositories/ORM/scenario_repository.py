from typing import Any
from uuid import UUID

from loguru import logger as log
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.database.db_contract.i_scenario_repo import IScenarioRepository
from apps.common.database.model_orm.scenario import CharacterScenarioState, ScenarioMaster, ScenarioNode


class ScenarioRepositoryORM(IScenarioRepository):
    """
    Реализация репозитория сценариев на SQLAlchemy 2.0.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        log.debug(f"ScenarioRepositoryORM | status=initialized session={session}")

    # --- 1. Работа с Scenario_Master (Table A) ---

    async def get_master(self, quest_key: str) -> dict[str, Any] | None:
        """Получает глобальные настройки квеста."""
        log.debug(f"ScenarioRepositoryORM | action=get_master quest_key='{quest_key}'")
        stmt = select(ScenarioMaster).where(ScenarioMaster.quest_key == quest_key)
        try:
            result = await self.session.execute(stmt)
            obj = result.scalar_one_or_none()
            return obj.__dict__ if obj else None
        except SQLAlchemyError:
            log.exception(f"ScenarioRepositoryORM | action=get_master status=failed quest_key='{quest_key}'")
            return None

    # --- 2. Работа с Scenario_Nodes (Table B) ---

    async def get_node(self, quest_key: str, node_key: str) -> dict[str, Any] | None:
        """Получает данные конкретной сцены."""
        log.debug(f"ScenarioRepositoryORM | action=get_node quest='{quest_key}' node='{node_key}'")
        stmt = select(ScenarioNode).where(ScenarioNode.quest_key == quest_key, ScenarioNode.node_key == node_key)
        try:
            result = await self.session.execute(stmt)
            obj = result.scalar_one_or_none()
            return obj.__dict__ if obj else None
        except SQLAlchemyError:
            log.exception(
                f"ScenarioRepositoryORM | action=get_node status=failed quest='{quest_key}' node='{node_key}'"
            )
            return None

    async def get_nodes_by_pool(self, quest_key: str, pool_tag: str) -> list[dict[str, Any]]:
        """Поиск нод по значению внутри JSON-поля."""
        log.debug(f"ScenarioRepositoryORM | action=get_nodes_by_pool quest='{quest_key}' pool='{pool_tag}'")
        try:
            # Используем .astext для PostgreSQL JSONB
            # Это стандартный способ извлечения текста из JSON в SQLAlchemy для PG
            stmt = select(ScenarioNode).where(
                ScenarioNode.quest_key == quest_key, ScenarioNode.selection_requirements["pool"].astext == pool_tag
            )
            result = await self.session.execute(stmt)
            return [n.__dict__ for n in result.scalars().all()]
        except SQLAlchemyError:
            log.exception(
                f"ScenarioRepositoryORM | action=get_nodes_by_pool status=failed quest='{quest_key}' pool='{pool_tag}'"
            )
            return []

    async def get_all_quest_nodes(self, quest_key: str) -> list[dict[str, Any]]:
        """Загружает все ноды квеста."""
        log.debug(f"ScenarioRepositoryORM | action=get_all_quest_nodes quest='{quest_key}'")
        stmt = select(ScenarioNode).where(ScenarioNode.quest_key == quest_key)
        try:
            result = await self.session.execute(stmt)
            return [n.__dict__ for n in result.scalars().all()]
        except SQLAlchemyError:
            log.exception(f"ScenarioRepositoryORM | action=get_all_quest_nodes status=failed quest='{quest_key}'")
            return []

    # --- 3. Работа с Character_Quest_State (Table C) ---

    async def get_active_state(self, char_id: int) -> dict[str, Any] | None:
        """Загружает сохраненное состояние сессии игрока."""
        log.debug(f"ScenarioRepositoryORM | action=get_active_state char_id={char_id}")
        stmt = select(CharacterScenarioState).where(CharacterScenarioState.char_id == char_id)
        try:
            result = await self.session.execute(stmt)
            obj = result.scalar_one_or_none()
            return obj.__dict__ if obj else None
        except SQLAlchemyError:
            log.exception(f"ScenarioRepositoryORM | action=get_active_state status=failed char_id={char_id}")
            return None

    async def upsert_state(
        self, char_id: int, quest_key: str, node_key: str, context: dict[str, Any], session_id: UUID
    ) -> None:
        """Обновление состояния через PostgreSQL Upsert."""
        log.debug(
            f"ScenarioRepositoryORM | action=upsert_state char_id={char_id} quest='{quest_key}' node='{node_key}'"
        )
        try:
            data = {
                "char_id": char_id,
                "quest_key": quest_key,
                "current_node_key": node_key,
                "context": context,
                "session_id": session_id,
                "updated_at": func.now(),  # Используем серверное время БД
            }

            stmt = insert(CharacterScenarioState).values(**data)

            # Упрощенный блок обновления для SQLAlchemy 2.0
            stmt = stmt.on_conflict_do_update(
                index_elements=["char_id"], set_={k: v for k, v in data.items() if k != "char_id"}
            )

            await self.session.execute(stmt)
            await self.session.commit()
        except SQLAlchemyError:
            log.exception(f"ScenarioRepositoryORM | action=upsert_state status=failed char_id={char_id}")
            await self.session.rollback()
            raise

    async def delete_state(self, char_id: int) -> None:
        """Удаляет запись о состоянии."""
        log.debug(f"ScenarioRepositoryORM | action=delete_state char_id={char_id}")
        stmt = delete(CharacterScenarioState).where(CharacterScenarioState.char_id == char_id)
        try:
            await self.session.execute(stmt)
            await self.session.commit()
        except SQLAlchemyError:
            log.exception(f"ScenarioRepositoryORM | action=delete_state status=failed char_id={char_id}")
            await self.session.rollback()
            raise
