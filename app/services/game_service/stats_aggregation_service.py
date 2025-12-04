from collections import defaultdict
from typing import Any, TypedDict

from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from app.resources.schemas_dto.character_dto import CharacterStatsReadDTO
from app.resources.schemas_dto.item_dto import InventoryItemDTO, ItemType
from app.services.game_service.modifiers_calculator_service import ModifiersCalculatorService
from database.repositories import get_character_stats_repo, get_inventory_repo


class StatInfo(TypedDict):
    """
    Представляет агрегированную информацию о характеристике,
    включая её итоговое значение и источники.
    """

    total: int | float
    sources: dict[str, int | float]


ItemList = list[InventoryItemDTO]
PoolDict = dict[str, StatInfo]


class StatsAggregationService:
    """
    Сервис-агрегатор для сбора и расчета всех характеристик персонажа.

    Оркестрирует получение базовых характеристик из БД, бонусов от экипировки,
    а также расчет производных модификаторов через `ModifiersCalculatorService`.
    """

    def __init__(self, session: AsyncSession):
        """
        Инициализирует StatsAggregationService.

        Args:
            session: Асинхронная сессия базы данных.
        """
        self.session = session
        self.stats_repo = get_character_stats_repo(session)
        self.inv_repo = get_inventory_repo(session)
        log.debug("StatsAggregationService | status=initialized")

    async def get_character_total_stats(self, char_id: int) -> dict[str, dict[str, StatInfo]]:
        """
        Возвращает полный слепок всех характеристик и модификаторов персонажа.
        """
        log.info(f"StatsAggregation | event=start_aggregation char_id={char_id}")

        def factory() -> StatInfo:
            return {"total": 0, "sources": {}}

        stats_pool: defaultdict[str, StatInfo] = defaultdict(factory)
        modifiers_pool: defaultdict[str, StatInfo] = defaultdict(factory)

        base_stats_dto = await self.stats_repo.get_stats(char_id)
        if not base_stats_dto:
            log.error(f"StatsAggregation | status=failed reason='Base stats not found' char_id={char_id}")
            return {}

        equipped_items: ItemList = await self.inv_repo.get_items_by_location(char_id, "equipped")
        base_keys = set(CharacterStatsReadDTO.model_fields.keys())

        self._process_base_stats(char_id, stats_pool, base_stats_dto, base_keys)
        self._process_equipment_stats(stats_pool, equipped_items, base_keys)

        total_stats_dto = self._create_stats_dto_from_pool(stats_pool, base_stats_dto)
        derived_mods_dto = ModifiersCalculatorService.calculate_all_modifiers_for_stats(total_stats_dto)

        self._add_layer(
            pool=modifiers_pool,
            source_name="📊 От характеристик",
            data=derived_mods_dto.model_dump(),
            target_keys=None,
        )

        self._process_equipment_modifiers(modifiers_pool, equipped_items, base_keys)

        log.info(f"StatsAggregation | status=finished char_id={char_id}")
        return {"stats": dict(stats_pool), "modifiers": dict(modifiers_pool)}

    def _process_base_stats(self, char_id: int, pool: PoolDict, dto: CharacterStatsReadDTO, keys: set[str]) -> None:
        """
        Обрабатывает базовые характеристики персонажа и добавляет их в пул.
        """
        data = dto.model_dump(exclude={"created_at", "updated_at", "character_id"})
        self._add_layer(pool=pool, source_name="👤 База", data=data, target_keys=keys)
        log.debug(f"StatsAggregation | action=process_base_stats char_id={char_id}")

    def _process_equipment_stats(self, pool: PoolDict, items: ItemList, keys: set[str]) -> None:
        """
        Обрабатывает бонусы от экипированных предметов к первичным характеристикам.
        """
        for item in items:
            if item.item_type in (ItemType.RESOURCE, ItemType.CURRENCY, ItemType.CONSUMABLE):
                continue
            else:
                bonuses = self._extract_total_bonuses(item)
                item_name = item.data.name
                self._add_layer(pool=pool, source_name=item_name, data=bonuses, target_keys=keys)
                log.debug(f"StatsAggregation | action=process_equipment_stats item='{item_name}'")

    def _process_equipment_modifiers(self, pool: PoolDict, items: ItemList, keys: set[str]) -> None:
        """
        Обрабатывает прямые бонусы от экипированных предметов к модификаторам.
        """
        for item in items:
            if item.item_type in (ItemType.RESOURCE, ItemType.CURRENCY, ItemType.CONSUMABLE):
                continue
            else:
                bonuses = self._extract_total_bonuses(item)
                item_name = item.data.name
                mod_bonuses = {k: v for k, v in bonuses.items() if k not in keys}
                self._add_layer(pool=pool, source_name=item_name, data=mod_bonuses, target_keys=None)
                log.debug(f"StatsAggregation | action=process_equipment_modifiers item='{item_name}'")

    @staticmethod
    def _extract_total_bonuses(item: InventoryItemDTO) -> dict[str, int | float]:
        """
        Извлекает все применимые бонусы из предмета.
        """
        if item.item_type in (ItemType.RESOURCE, ItemType.CURRENCY, ItemType.CONSUMABLE):
            return {}
        else:
            total = item.data.bonuses.copy() if item.data.bonuses else {}

            if item.item_type == ItemType.WEAPON:
                avg_dmg = (item.data.damage_min + item.data.damage_max) / 2
                total["physical_damage_bonus"] = total.get("physical_damage_bonus", 0) + avg_dmg
            elif item.item_type == ItemType.ARMOR:
                if item.data.protection:
                    total["physical_resistance"] = total.get("physical_resistance", 0) + item.data.protection
            return total

    @staticmethod
    def _add_layer(pool: PoolDict, source_name: str, data: dict[str, Any], target_keys: set[str] | None = None) -> None:
        """
        Добавляет слой бонусов от источника в указанный пул.
        """
        for key, value in data.items():
            if target_keys is not None and key not in target_keys:
                continue
            if not isinstance(value, (int, float)):
                continue
            pool[key]["sources"][source_name] = value
            pool[key]["total"] += value
        log.debug(f"StatsAggregation | action=add_layer source='{source_name}' keys={list(data.keys())}")

    @staticmethod
    def _create_stats_dto_from_pool(stats_pool: PoolDict, template: CharacterStatsReadDTO) -> CharacterStatsReadDTO:
        """
        Создает DTO `CharacterStatsReadDTO` на основе агрегированного пула характеристик.
        """
        final_data = template.model_dump()
        for stat_name, stat_data in stats_pool.items():
            if stat_name in final_data:
                final_data[stat_name] = int(stat_data["total"])
        return CharacterStatsReadDTO(**final_data)
