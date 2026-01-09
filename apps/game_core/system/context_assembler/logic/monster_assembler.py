# apps/game_core/system/context_assembler/logic/monster_assembler.py
import uuid
from typing import Any

from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.database.repositories.ORM.monster_repository import MonsterRepository
from apps.common.services.redis.manager.account_manager import AccountManager
from apps.common.services.redis.manager.context_manager import ContextRedisManager
from apps.game_core.system.context_assembler.logic.base_assembler import BaseAssembler
from apps.game_core.system.context_assembler.schemas.monster_temp_context import MonsterTempContextSchema


class MonsterAssembler(BaseAssembler):
    """
    Стратегия сборки контекста для Монстров.
    """

    def __init__(self, session: AsyncSession, account_manager: AccountManager, context_manager: ContextRedisManager):
        self.session = session
        self.account_manager = account_manager
        self.context_manager = context_manager
        self.monster_repo = MonsterRepository(session)

    async def process_batch(self, ids: list[Any], scope: str) -> tuple[dict[Any, str], list[Any]]:
        """
        Пакетная обработка монстров.
        """
        log.debug(f"MonsterAssembler | processing batch count={len(ids)} scope={scope}")

        if not ids:
            return {}, []

        # Ensure ids are strings
        str_ids = [str(i) for i in ids]

        try:
            monsters_orm = await self.monster_repo.get_monsters_batch(str_ids)
        except Exception as e:  # noqa: BLE001
            log.exception(f"MonsterAssembler | DB fetch failed. Error: {e}")
            return {}, str_ids

        monsters_map = {str(m.id): m for m in monsters_orm}

        success_map = {}
        error_list = []
        contexts_to_save = {}

        for m_id in str_ids:
            monster_orm = monsters_map.get(m_id)
            if not monster_orm:
                error_list.append(m_id)
                continue

            try:
                # Используем MonsterTempContextSchema
                context_schema = MonsterTempContextSchema(
                    core_stats=monster_orm.scaled_base_stats,
                    core_loadout=monster_orm.loadout_ids,
                    core_skills=monster_orm.skills_snapshot,
                    core_meta={
                        "id": m_id,
                        "name": monster_orm.name_ru,  # Используем name_ru как основное имя
                        "role": monster_orm.role,
                        "threat": monster_orm.threat_rating,
                        "clan_id": str(monster_orm.clan_id),
                    },
                )

                context_data = context_schema.model_dump(by_alias=True)

                redis_key = f"temp:setup:{uuid.uuid4()}"
                success_map[m_id] = redis_key
                contexts_to_save[m_id] = (redis_key, context_data)
            except Exception as e:  # noqa: BLE001
                log.error(f"MonsterAssembler | transform failed for {m_id}: {e}")
                error_list.append(m_id)

        # Cast contexts_to_save to match ContextRedisManager signature if needed,
        # but ContextRedisManager usually accepts dict[int|str, ...]
        await self.context_manager.save_context_batch(contexts_to_save)  # type: ignore

        log.info(f"MonsterAssembler | batch processed. success={len(success_map)}, errors={len(error_list)}")
        return success_map, error_list
