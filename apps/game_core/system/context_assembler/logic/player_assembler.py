# apps/game_core/system/context_assembler/logic/player_assembler.py
import asyncio
import uuid
from typing import Any

from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.database.repositories import (
    get_character_stats_repo,
    get_inventory_repo,
    get_skill_progress_repo,
)
from apps.common.enums.stats_enum import PrimaryStat
from apps.common.schemas_dto.character_dto import CharacterStatsReadDTO
from apps.common.schemas_dto.skill import SkillProgressDTO
from apps.common.services.core_service.manager.account_manager import AccountManager
from apps.common.services.core_service.manager.context_manager import ContextRedisManager
from apps.game_core.system.context_assembler.logic.base_assembler import BaseAssembler
from apps.game_core.system.context_assembler.utils import format_value


class PlayerAssembler(BaseAssembler):
    """
    Стратегия сборки контекста для Игроков.
    Собирает данные из PostgreSQL (Stats, Inventory, Skills) и формирует JSON для Redis.
    """

    def __init__(self, session: AsyncSession, account_manager: AccountManager, context_manager: ContextRedisManager):
        self.session = session
        self.account_manager = account_manager
        self.context_manager = context_manager
        self.stats_repo = get_character_stats_repo(session)
        self.inv_repo = get_inventory_repo(session)
        self.skill_repo = get_skill_progress_repo(session)

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
            stats_task = self.stats_repo.get_stats_batch(int_ids)
            skills_task = self.skill_repo.get_all_skills_progress_batch(int_ids)
            equip_task = self.inv_repo.get_items_by_location_batch(int_ids, "equipped")
            inv_task = self.inv_repo.get_items_by_location_batch(int_ids, "inventory")

            # Vitals из Redis (Batch Fetching через Pipeline)
            vitals_future = asyncio.create_task(self.account_manager.get_accounts_json_batch(int_ids, "vitals"))

            # Ждем всех
            fetched_data = await asyncio.gather(stats_task, skills_task, equip_task, inv_task, vitals_future)

            # Распаковываем результаты с ослабленной типизацией для сложных DTO
            stats_list: list[CharacterStatsReadDTO] = fetched_data[0]
            skills_map: dict[int, list[SkillProgressDTO]] = fetched_data[1]
            equipped_map: dict[int, list[Any]] = fetched_data[2]  # Any из-за сложного Union в DTO
            inventory_map: dict[int, list[Any]] = fetched_data[3]
            vitals_list: list[dict | None] = fetched_data[4]

        except Exception as e:  # noqa: BLE001
            log.exception(f"PlayerAssembler | DB fetch failed for batch. Error: {e}")
            return {}, int_ids

        # Преобразуем список статов в словарь для удобства
        stats_map = {stat.character_id: stat for stat in stats_list}
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

            stats = stats_map.get(char_id)
            skills = skills_map.get(char_id, [])
            equipped = equipped_map.get(char_id, [])
            inventory = inventory_map.get(char_id, [])
            vitals = vitals_map.get(char_id)

            try:
                # stats гарантированно CharacterStatsReadDTO, так как мы проверили наличие в map
                if stats:
                    context_data = self._transform_to_rbc_format(char_id, stats, skills, inventory, equipped, vitals)

                    redis_key = f"temp:setup:{uuid.uuid4()}"
                    success_map[char_id] = redis_key
                    contexts_to_save[char_id] = (redis_key, context_data)
            except Exception as e:  # noqa: BLE001
                log.error(f"PlayerAssembler | transform failed for {char_id}: {e}")
                error_list.append(char_id)

        # 3. Массовое сохранение через ContextRedisManager
        await self.context_manager.save_context_batch(contexts_to_save)  # type: ignore

        log.info(f"PlayerAssembler | batch processed. success={len(success_map)}, errors={len(error_list)}")
        return success_map, error_list

    def _transform_to_rbc_format(
        self,
        char_id: int,
        stats: CharacterStatsReadDTO,
        skills: list[SkillProgressDTO],
        inventory: list[Any],
        equipped: list[Any],
        vitals: dict | None,
    ) -> dict[str, Any]:
        """
        Превращает DTO в Action-Based Strings JSON (v:raw).
        """
        # Фильтрация пояса
        belt_items = [i.model_dump() for i in inventory if i.quick_slot_position]

        # Фильтрация активных скиллов
        active_skills = [s.skill_key for s in skills if s.is_unlocked]

        # Сборка v:raw (Math Model)
        math_model: dict[str, Any] = {
            "attributes": {},
            "modifiers": {},
            "tags": ["player", "human"],  # TODO: Брать расу из био
        }

        # Атрибуты (Base) - Internal
        # Используем model_dump для безопасного доступа к полям
        stats_dict = stats.model_dump()
        for stat_enum in PrimaryStat:
            field = stat_enum.value
            val = stats_dict.get(field, 0)
            math_model["attributes"][field] = {"base": str(float(val)), "flats": {}, "percents": {}}

        # TODO: Рассчитать бонусы от Скиллов (XP -> Level -> Bonus) и добавить в math_model (Internal)
        # Сейчас мы просто передаем список ключей в loadout, но не учитываем их влияние на статы.

        # Экипировка -> Modifiers - External
        for item in equipped:
            # Бонусы
            if item.data and item.data.bonuses:
                for stat, val in item.data.bonuses.items():
                    # Используем format_value для умного преобразования (* или +)
                    val_str = format_value(stat, val, source_type="external")

                    # Проверяем, является ли стат атрибутом (через Enum)
                    is_attribute = False
                    try:
                        PrimaryStat(stat)
                        is_attribute = True
                    except ValueError:
                        pass

                    if is_attribute:
                        # Атрибуты всегда аддитивные, пишем в flats
                        # Явное приведение типа для успокоения IDE
                        attr_data: dict = math_model["attributes"][stat]
                        attr_data["flats"][f"item:{item.item_id}"] = val_str
                    else:
                        # Модификаторы пишем в sources
                        self._add_modifier(math_model, stat, val, f"item:{item.item_id}")

            # Оружие (Базовый урон)
            if item.item_type == "weapon":
                dmg_min = item.data.damage_min
                dmg_max = item.data.damage_max
                if dmg_min:
                    self._add_modifier(math_model, "physical_damage_min", dmg_min, f"item:{item.item_id}")
                if dmg_max:
                    self._add_modifier(math_model, "physical_damage_max", dmg_max, f"item:{item.item_id}")

            # Броня (Локальная защита)
            if item.item_type == "armor":
                prot = item.data.protection
                if prot:
                    # Маппинг слотов на поля DTO
                    slot_map = {
                        "head_armor": "armor_head",
                        "chest_armor": "armor_chest",
                        "arms_armor": "armor_arms",
                        "legs_armor": "armor_legs",
                        "feet_armor": "armor_feet",
                    }
                    target_field = slot_map.get(item.slot)

                    if target_field:
                        self._add_modifier(math_model, target_field, prot, f"item:{item.item_id}")
                    else:
                        # Fallback для неизвестных слотов
                        self._add_modifier(math_model, "damage_reduction_flat", prot, f"item:{item.item_id}")

        # Vitals
        # vitals - это словарь {"hp": {"cur": 100, "max": 100}, ...}
        hp = 100
        en = 100
        if vitals and isinstance(vitals, dict):
            hp = vitals.get("hp", {}).get("cur", 100)
            en = vitals.get("energy", {}).get("cur", 100)

        return {
            "meta": {"entity_id": char_id, "type": "player", "timestamp": 0},
            "math_model": math_model,
            "loadout": {
                "belt": belt_items,
                "skills": active_skills,
                "abilities": [],  # TODO: Заглушка. Список активных абилок (вычисляется или из БД)
            },
            "vitals": {"hp_current": hp, "energy_current": en},
        }

    def _add_modifier(self, model: dict, key: str, value: Any, source: str):
        """Хелпер для добавления модификатора."""
        if not value:
            return
        if key not in model["modifiers"]:
            model["modifiers"][key] = {"sources": {}}
        # Базовые статы предметов (урон, броня) считаются external, но format_value знает, что они аддитивные
        # А бонусы (крит) станут мультипликаторами
        model["modifiers"][key]["sources"][source] = format_value(key, value, "external")
