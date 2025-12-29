# apps/game_core/system/context_assembler/logic/monster_assembler.py
import uuid
from typing import Any, cast

from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.database.repositories.ORM.monster_repository import MonsterRepository
from apps.common.services.core_service.manager.account_manager import AccountManager
from apps.common.services.core_service.manager.context_manager import ContextRedisManager
from apps.game_core.system.context_assembler.logic.base_assembler import BaseAssembler
from apps.game_core.system.context_assembler.logic.helpers.monster_data_helper import get_equipment_modifiers


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
                context_data = self._transform_to_rbc_format(m_id, monster_orm)

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

    def _transform_to_rbc_format(self, m_id: str, orm_obj) -> dict[str, Any]:
        """
        Превращает GeneratedMonsterORM в Action-Based Strings JSON.
        """
        math_model: dict[str, Any] = {"attributes": {}, "modifiers": {}, "tags": ["monster", orm_obj.role]}

        # 1. Атрибуты (Internal)
        raw_stats = orm_obj.scaled_base_stats
        if raw_stats and isinstance(raw_stats, dict):
            # Mypy теперь точно знает, что raw_stats это dict
            for stat, val in raw_stats.items():
                if val:
                    math_model["attributes"][stat] = {"base": str(val), "flats": {}, "percents": {}}

        # 2. Модификаторы (External)
        equipment_modifiers = get_equipment_modifiers(orm_obj.loadout_ids)

        for stat, data in equipment_modifiers.items():
            # Явно кастим data к словарю, чтобы Mypy не ругался на .items()
            data_dict = cast(dict[str, Any], data)
            sources = data_dict.get("sources", {})

            if not isinstance(sources, dict):
                continue

            if stat in math_model["attributes"]:
                for source, val_str in sources.items():
                    math_model["attributes"][stat]["flats"][source] = val_str
            else:
                if stat not in math_model["modifiers"]:
                    math_model["modifiers"][stat] = {"sources": {}}

                for source, val_str in sources.items():
                    math_model["modifiers"][stat]["sources"][source] = val_str

        # 3. Абилки
        abilities = []
        raw_skills = orm_obj.skills_snapshot

        if raw_skills:
            if isinstance(raw_skills, dict):
                for s in raw_skills:
                    # Предполагаем, что ключи - это строки или объекты с id
                    if isinstance(s, dict) and "id" in s:
                        abilities.append(str(s["id"]))
                    else:
                        abilities.append(str(s))
            elif isinstance(raw_skills, list):
                for s in raw_skills:
                    if isinstance(s, dict) and "id" in s:
                        abilities.append(str(s["id"]))
                    else:
                        abilities.append(str(s))

        # TODO: Добавить бонусы Клана (когда появятся в БД)

        return {
            "meta": {"entity_id": m_id, "type": "monster", "timestamp": 0},
            "math_model": math_model,
            "loadout": {
                "belt": [],
                "abilities": abilities,  # У монстров абилки, а не скиллы
            },
            "vitals": {
                "hp_current": -1,  # -1 означает "рассчитать и установить максимум"
                "energy_current": -1,
            },
        }
