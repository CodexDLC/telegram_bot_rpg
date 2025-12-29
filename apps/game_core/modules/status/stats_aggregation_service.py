from collections import defaultdict
from typing import Any, TypedDict

from loguru import logger as log
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.database.repositories import get_character_stats_repo, get_inventory_repo
from apps.common.schemas_dto import CharacterStatsReadDTO, InventoryItemDTO, ItemType
from apps.game_core.modules.status.modifiers_calculator_service import ModifiersCalculatorService


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

    Собирает базовые статы, бонусы от экипировки, рассчитывает производные
    модификаторы и возвращает полный слепок всех данных для UI или других сервисов.
    """

    def __init__(self, session: AsyncSession):
        """
        Инициализирует сервис.

        Args:
            session: Сессия БД.
        """
        self.session = session
        self.stats_repo = get_character_stats_repo(session)
        self.inv_repo = get_inventory_repo(session)
        log.debug("StatsAggregationServiceInit")

    async def get_character_total_stats(self, char_id: int) -> dict[str, dict[str, StatInfo]]:
        """
        Возвращает полный слепок всех характеристик и модификаторов персонажа.

        Собирает данные из БД (статы, инвентарь), рассчитывает производные
        модификаторы и агрегирует все в единую структуру.

        Args:
            char_id: ID персонажа.

        Returns:
            Словарь с двумя ключами: 'stats' и 'modifiers', содержащий
            детальную информацию по каждой характеристике.
        """
        log.info(f"GetTotalStats | event=start char_id={char_id}")

        def factory() -> StatInfo:
            return {"total": 0, "sources": {}}

        stats_pool: defaultdict[str, StatInfo] = defaultdict(factory)
        modifiers_pool: defaultdict[str, StatInfo] = defaultdict(factory)

        try:
            base_stats_dto = await self.stats_repo.get_stats(char_id)
            if not base_stats_dto:
                log.warning(f"GetTotalStatsFail | reason=no_base_stats char_id={char_id}")
                return {}

            equipped_items: ItemList = await self.inv_repo.get_items_by_location(char_id, "equipped")
        except SQLAlchemyError:
            log.exception(f"GetTotalStatsError | reason=db_error char_id={char_id}")
            return {}

        base_keys = set(CharacterStatsReadDTO.model_fields.keys())

        self._process_base_stats(char_id, stats_pool, base_stats_dto, base_keys)
        has_weapon = self._process_equipment_stats(stats_pool, equipped_items, base_keys)

        total_stats_dto = self._create_stats_dto_from_pool(stats_pool, base_stats_dto)
        derived_mods_dto = ModifiersCalculatorService.calculate_all_modifiers_for_stats(total_stats_dto)

        self._add_layer(
            pool=modifiers_pool,
            source_name="📊 От характеристик",
            data=derived_mods_dto.model_dump(),
            target_keys=None,
        )

        self._process_equipment_modifiers(modifiers_pool, equipped_items, base_keys)

        if not has_weapon:
            self._apply_unarmed_spread(modifiers_pool)

        log.info(f"GetTotalStats | event=success char_id={char_id}")
        return {"stats": dict(stats_pool), "modifiers": dict(modifiers_pool)}

    def _process_base_stats(self, char_id: int, pool: PoolDict, dto: CharacterStatsReadDTO, keys: set[str]) -> None:
        """Обрабатывает базовые характеристики персонажа."""
        data = dto.model_dump(exclude={"created_at", "updated_at", "character_id"})
        self._add_layer(pool=pool, source_name="👤 База", data=data, target_keys=keys)
        log.debug(f"ProcessBaseStats | char_id={char_id}")

    def _process_equipment_stats(self, pool: PoolDict, items: ItemList, keys: set[str]) -> bool:
        """Обрабатывает бонусы к базовым статам от экипировки."""
        has_weapon = False
        for item in items:
            if item.item_type == ItemType.WEAPON:
                has_weapon = True

            if item.item_type not in (ItemType.RESOURCE, ItemType.CURRENCY, ItemType.CONSUMABLE):
                bonuses = self._extract_total_bonuses(item)
                item_name = item.data.name
                self._add_layer(pool=pool, source_name=item_name, data=bonuses, target_keys=keys)
        return has_weapon

    def _process_equipment_modifiers(self, pool: PoolDict, items: ItemList, keys: set[str]) -> None:
        """Обрабатывает бонусы к производным модификаторам от экипировки."""
        for item in items:
            if item.item_type not in (ItemType.RESOURCE, ItemType.CURRENCY, ItemType.CONSUMABLE):
                bonuses = self._extract_total_bonuses(item)
                item_name = item.data.name
                mod_bonuses = {k: v for k, v in bonuses.items() if k not in keys}
                self._add_layer(pool=pool, source_name=item_name, data=mod_bonuses, target_keys=None)

    def _apply_unarmed_spread(self, pool: PoolDict) -> None:
        """Применяет разброс +/- 20% к базовому урону, если нет оружия."""
        if "physical_damage_min" not in pool:
            return
        base_dmg = pool["physical_damage_min"]["total"]  # min и max равны на этом этапе
        spread = 0.20

        min_dmg = base_dmg * (1 - spread)
        max_dmg = base_dmg * (1 + spread)

        pool["physical_damage_min"]["total"] = min_dmg
        pool["physical_damage_max"]["total"] = max_dmg

        log.debug(f"ApplyUnarmedSpread | base_dmg={base_dmg} spread={spread} damage=({min_dmg:.1f}-{max_dmg:.1f})")

    @staticmethod
    def _extract_total_bonuses(item: InventoryItemDTO) -> dict[str, int | float]:
        """Извлекает все числовые бонусы из предмета, включая урон/защиту."""
        if item.item_type in (ItemType.RESOURCE, ItemType.CURRENCY, ItemType.CONSUMABLE):
            return {}

        total = item.data.bonuses.copy() if item.data.bonuses else {}

        if item.item_type == ItemType.WEAPON:
            total["physical_damage_min"] = total.get("physical_damage_min", 0) + item.data.damage_min
            total["physical_damage_max"] = total.get("physical_damage_max", 0) + item.data.damage_max
        elif item.item_type == ItemType.ARMOR:
            if item.data.protection:
                total["damage_reduction_flat"] = total.get("damage_reduction_flat", 0) + item.data.protection
        return total

    @staticmethod
    def _add_layer(pool: PoolDict, source_name: str, data: dict[str, Any], target_keys: set[str] | None = None) -> None:
        """Добавляет слой бонусов в указанный пул."""
        for key, value in data.items():
            if target_keys is not None and key not in target_keys:
                continue
            if not isinstance(value, (int, float)):
                continue
            pool[key]["sources"][source_name] = value
            pool[key]["total"] += value

    @staticmethod
    def _create_stats_dto_from_pool(stats_pool: PoolDict, template: CharacterStatsReadDTO) -> CharacterStatsReadDTO:
        """Создает DTO с итоговыми базовыми статами из пула."""
        final_data = template.model_dump()
        for stat_name, stat_data in stats_pool.items():
            if stat_name in final_data:
                final_data[stat_name] = int(stat_data["total"])
        return CharacterStatsReadDTO(**final_data)
