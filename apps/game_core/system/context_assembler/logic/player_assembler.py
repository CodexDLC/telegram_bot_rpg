# apps/game_core/system/context_assembler/logic/player_assembler.py
import asyncio
import uuid
from typing import Any, cast

from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.database.model_orm.symbiote import CharacterSymbiote
from apps.common.database.repositories import (
    get_character_repo,
    get_character_stats_repo,
    get_inventory_repo,
    get_skill_progress_repo,
    get_symbiote_repo,
)
from apps.common.schemas_dto.character_dto import CharacterReadDTO, CharacterStatsReadDTO
from apps.common.schemas_dto.skill import SkillProgressDTO
from apps.common.services.core_service.manager.account_manager import AccountManager
from apps.common.services.core_service.manager.context_manager import ContextRedisManager
from apps.game_core.system.context_assembler.logic.base_assembler import BaseAssembler
from apps.game_core.system.context_assembler.schemas.temp_context import TempContextSchema


class PlayerAssembler(BaseAssembler):
    """
    Стратегия сборки контекста для Игроков.
    Собирает данные из PostgreSQL (Stats, Inventory, Skills) и формирует JSON для Redis.
    """

    def __init__(self, session: AsyncSession, account_manager: AccountManager, context_manager: ContextRedisManager):
        self.session = session
        self.account_manager = account_manager
        self.context_manager = context_manager
        self.char_repo = get_character_repo(session)
        self.stats_repo = get_character_stats_repo(session)
        self.inv_repo = get_inventory_repo(session)
        self.skill_repo = get_skill_progress_repo(session)
        self.symbiote_repo = get_symbiote_repo(session)

    async def process_batch(self, ids: list[Any], scope: str) -> tuple[dict[Any, str], list[Any]]:
        """
        Реализация пакетной обработки игроков.
        """
        log.debug(f"PlayerAssembler | processing batch count={len(ids)}")

        if not ids:
            return {}, []

        # Ensure ids are ints
        int_ids = [int(i) for i in ids]

        # 1. Пакетный сбор данных (3 запроса к БД)
        try:
            # Запускаем запросы параллельно
            char_task = self.char_repo.get_characters_batch(int_ids)
            stats_task = self.stats_repo.get_stats_batch(int_ids)
            skills_task = self.skill_repo.get_all_skills_progress_batch(int_ids)
            equip_task = self.inv_repo.get_items_by_location_batch(int_ids, "equipped")
            inv_task = self.inv_repo.get_items_by_location_batch(int_ids, "inventory")
            symbiote_task = self.symbiote_repo.get_symbiotes_batch(int_ids)

            # Vitals из Redis (Batch Fetching через Pipeline)
            vitals_future = asyncio.create_task(self.account_manager.get_accounts_json_batch(int_ids, "vitals"))

            # Ждем всех
            fetched_data = await asyncio.gather(
                char_task, stats_task, skills_task, equip_task, inv_task, symbiote_task, vitals_future
            )

            # Распаковываем результаты с явным приведением типов
            chars_list = cast(list[CharacterReadDTO], fetched_data[0])
            stats_list = cast(list[CharacterStatsReadDTO], fetched_data[1])
            skills_map = cast(dict[int, list[SkillProgressDTO]], fetched_data[2])
            equipped_map = cast(dict[int, list[Any]], fetched_data[3])
            inventory_map = cast(dict[int, list[Any]], fetched_data[4])
            symbiotes_list = cast(list[CharacterSymbiote], fetched_data[5])
            vitals_list = cast(list[dict | None], fetched_data[6])

        except Exception as e:  # noqa: BLE001
            log.exception(f"PlayerAssembler | DB fetch failed for batch. Error: {e}")
            return {}, int_ids

        # Преобразуем список статов в словарь для удобства
        chars_map = {char.character_id: char for char in chars_list}
        stats_map = {stat.character_id: stat for stat in stats_list}
        symbiotes_map = {s.character_id: s for s in symbiotes_list}
        # vitals_list уже соответствует порядку ids, так как get_accounts_json_batch это гарантирует
        vitals_map = {char_id: vitals for char_id, vitals in zip(int_ids, vitals_list, strict=False)}

        # 2. Трансформация и подготовка к сохранению
        success_map = {}
        error_list = []
        contexts_to_save = {}

        for char_id in int_ids:
            if char_id not in stats_map:
                error_list.append(char_id)
                continue

            char_info = chars_map.get(char_id)
            stats = stats_map.get(char_id)
            skills = skills_map.get(char_id, [])
            equipped = equipped_map.get(char_id, [])
            inventory = inventory_map.get(char_id, [])
            vitals = vitals_map.get(char_id)
            symbiote = symbiotes_map.get(char_id)

            try:
                # stats гарантированно CharacterStatsReadDTO, так как мы проверили наличие в map
                if stats and char_info:
                    # Маппинг симбиота (ORM -> dict)
                    symbiote_data = None
                    if symbiote:
                        # Ручной маппинг, так как ORM не имеет model_dump
                        symbiote_data = {
                            "symbiote_name": symbiote.symbiote_name,
                            "gift_id": symbiote.gift_id,
                            "gift_rank": symbiote.gift_rank,
                            "gift_xp": symbiote.gift_xp,
                            "elements_resonance": symbiote.elements_resonance,
                        }

                    # Используем TempContextSchema для сборки
                    context_schema = TempContextSchema(
                        core_stats=stats,
                        core_inventory=equipped + inventory,  # Объединяем для полноты
                        core_skills=skills,
                        core_vitals=vitals if vitals else {},
                        core_meta=char_info,
                        core_symbiote=symbiote_data,
                    )

                    # Получаем готовый JSON для Redis
                    context_data = context_schema.model_dump(by_alias=True)

                    redis_key = f"temp:setup:{uuid.uuid4()}"
                    success_map[char_id] = redis_key
                    contexts_to_save[char_id] = (redis_key, context_data)
                else:
                    log.warning(f"PlayerAssembler | missing core data for {char_id}")
                    error_list.append(char_id)
            except Exception as e:  # noqa: BLE001
                log.error(f"PlayerAssembler | transform failed for {char_id}: {e}")
                error_list.append(char_id)

        # 3. Массовое сохранение через ContextRedisManager
        await self.context_manager.save_context_batch(contexts_to_save)  # type: ignore

        log.info(f"PlayerAssembler | batch processed. success={len(success_map)}, errors={len(error_list)}")
        return success_map, error_list
