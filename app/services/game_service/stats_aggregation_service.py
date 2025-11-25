from collections import defaultdict
from typing import TypedDict

from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from app.resources.schemas_dto.character_dto import CharacterStatsReadDTO
from app.resources.schemas_dto.item_dto import InventoryItemDTO, ItemType
from app.services.game_service.modifiers_calculator_service import ModifiersCalculatorService
from database.repositories import get_character_stats_repo, get_inventory_repo


# Определяем строгую структуру для пулов
class StatInfo(TypedDict):
    total: int | float
    sources: dict[str, int | float]


ItemList = list[InventoryItemDTO]
PoolDict = dict[str, StatInfo]


class StatsAggregationService:
    """
    Сервис-Агрегатор.
    Оркестрирует сбор характеристик из всех источников:
    1. База (из БД)
    2. Предметы (из Инвентаря)
    3. Расчетные модификаторы (через CalculatorService)
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.stats_repo = get_character_stats_repo(session)
        self.inv_repo = get_inventory_repo(session)

    async def get_character_total_stats(self, char_id: int) -> dict[str, dict[str, StatInfo]]:
        """
        Возвращает полный слепок силы персонажа.
        """
        log.debug(f"Начало агрегации статов для char_id={char_id}")

        def factory() -> StatInfo:
            return {"total": 0, "sources": {}}

        stats_pool: defaultdict[str, StatInfo] = defaultdict(factory)
        modifiers_pool: defaultdict[str, StatInfo] = defaultdict(factory)

        # 1. Загрузка данных
        base_stats_dto = await self.stats_repo.get_stats(char_id)
        if not base_stats_dto:
            log.error(f"Базовые статы не найдены для char_id={char_id}")
            return {}

        equipped_items: ItemList = await self.inv_repo.get_items_by_location(char_id, "equipped")
        base_keys = set(CharacterStatsReadDTO.model_fields.keys())

        # ==========================================
        # ЭТАП 1: Сбор ПЕРВИЧНЫХ ХАРАКТЕРИСТИК (Stats)
        # ==========================================
        self._process_base_stats(stats_pool, base_stats_dto, base_keys)
        self._process_equipment_stats(stats_pool, equipped_items, base_keys)

        # ==========================================
        # ЭТАП 2: Расчет ПРОИЗВОДНЫХ (Modifiers from Stats)
        # ==========================================
        total_stats_dto = self._create_stats_dto_from_pool(stats_pool, base_stats_dto)
        derived_mods_dto = ModifiersCalculatorService.calculate_all_modifiers_for_stats(total_stats_dto)

        self._add_layer(
            pool=modifiers_pool,
            source_name="📊 От характеристик",
            data=derived_mods_dto.model_dump(),
            target_keys=None,
        )

        # ==========================================
        # ЭТАП 3: Сбор ПРЯМЫХ БОНУСОВ К МОДИФИКАТОРАМ
        # ==========================================
        self._process_equipment_modifiers(modifiers_pool, equipped_items, base_keys)

        return {"stats": dict(stats_pool), "modifiers": dict(modifiers_pool)}

    # ==================================================
    # Приватные методы обработки
    # ==================================================

    def _process_base_stats(self, pool: PoolDict, dto: CharacterStatsReadDTO, keys: set[str]):
        data = dto.model_dump(exclude={"created_at", "updated_at", "character_id"})
        self._add_layer(pool=pool, source_name="👤 База", data=data, target_keys=keys)

    def _process_equipment_stats(self, pool: PoolDict, items: ItemList, keys: set[str]):
        for item in items:
            if item.item_type == ItemType.CONSUMABLE:
                continue
            bonuses = self._extract_total_bonuses(item)
            item_name = item.data.name
            self._add_layer(pool=pool, source_name=item_name, data=bonuses, target_keys=keys)

    def _process_equipment_modifiers(self, pool: PoolDict, items: ItemList, keys: set[str]):
        for item in items:
            if item.item_type == ItemType.CONSUMABLE:
                continue
            bonuses = self._extract_total_bonuses(item)
            item_name = item.data.name
            # Берем только то, чего НЕТ в списке первичных статов
            mod_bonuses = {k: v for k, v in bonuses.items() if k not in keys}
            self._add_layer(pool=pool, source_name=item_name, data=mod_bonuses, target_keys=None)

    @staticmethod
    def _extract_total_bonuses(item: InventoryItemDTO) -> dict[str, int | float]:
        if item.item_type == ItemType.CONSUMABLE:
            return {}
        total = item.data.bonuses.copy()
        # Специфичные бонусы
        if item.item_type == ItemType.WEAPON:
            avg_dmg = (item.data.damage_min + item.data.damage_max) / 2
            total["physical_damage_bonus"] = total.get("physical_damage_bonus", 0) + avg_dmg
        elif item.item_type == ItemType.ARMOR:
            if item.data.protection:
                total["physical_resistance"] = total.get("physical_resistance", 0) + item.data.protection
        return total

    @staticmethod
    def _add_layer(pool: PoolDict, source_name: str, data: dict, target_keys: set[str] | None = None):
        for key, value in data.items():
            if target_keys is not None and key not in target_keys:
                continue
            if not isinstance(value, (int, float)):
                continue
            pool[key]["sources"][source_name] = value
            pool[key]["total"] += value

    @staticmethod
    def _create_stats_dto_from_pool(stats_pool: PoolDict, template: CharacterStatsReadDTO) -> CharacterStatsReadDTO:
        final_data = template.model_dump()
        for stat_name, stat_data in stats_pool.items():
            if stat_name in final_data:
                final_data[stat_name] = int(stat_data["total"])
        return CharacterStatsReadDTO(**final_data)
