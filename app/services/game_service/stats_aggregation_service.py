# app/services/game_service/stats_aggregation_service.py
from collections import defaultdict
from typing import Any

from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from app.resources.schemas_dto.character_dto import CharacterStatsReadDTO
from app.resources.schemas_dto.item_dto import AccessoryItemDTO, ArmorItemDTO, WeaponItemDTO
from app.services.game_service.modifiers_calculator_service import ModifiersCalculatorService
from database.repositories import get_character_stats_repo, get_inventory_repo

# Определяем сложные типы для аннотаций
PoolDict = dict[str, dict[str, Any]]
ItemList = list[WeaponItemDTO | ArmorItemDTO | AccessoryItemDTO]


class StatsAggregationService:
    """
    Сервис-Агрегатор.
    Оркестрирует сбор характеристик из всех источников (БД, Предметы, Навыки).
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.stats_repo = get_character_stats_repo(session)
        self.inv_repo = get_inventory_repo(session)

    async def get_character_total_stats(self, char_id: int) -> dict[str, PoolDict]:
        """
        ГЛАВНЫЙ МЕТОД (Оркестратор).
        Вызывает этапы сборки по очереди. Добавлять новые механики (Пассивки, Баффы)
        нужно именно сюда, добавляя новые строчки вызова.
        """
        log.debug(f"Начало агрегации статов для char_id={char_id}")

        # 1. Инициализация контейнеров с явной аннотацией типа
        stats_pool: PoolDict = defaultdict(lambda: {"total": 0, "sources": {}})
        modifiers_pool: PoolDict = defaultdict(lambda: {"total": 0, "sources": {}})

        # 2. Загрузка "Сырых" данных (Data Fetching)
        base_stats_dto = await self.stats_repo.get_stats(char_id)
        if not base_stats_dto:
            log.error(f"Базовые статы не найдены для char_id={char_id}")
            return {}

        equipped_items: ItemList = await self.inv_repo.get_items_by_location(char_id, "equipped")

        # Кэшируем ключи базовых статов (для разделения мух и котлет)
        base_keys = set(CharacterStatsReadDTO.model_fields.keys())

        # ==========================================
        # ЭТАП 1: Сбор ПЕРВИЧНЫХ СТАТОВ
        # ==========================================

        self._process_base_stats(stats_pool, base_stats_dto, base_keys)
        self._process_equipment_stats(stats_pool, equipped_items, base_keys)

        # ==========================================
        # ЭТАП 2: Расчет ПРОИЗВОДНЫХ (Modifiers)
        # ==========================================

        total_stats_dto = self._create_stats_dto_from_pool(stats_pool, base_stats_dto)
        derived_mods_dto = ModifiersCalculatorService.calculate_all_modifiers_for_stats(total_stats_dto)

        self._add_layer(
            pool=modifiers_pool, source_name="from_stats", data=derived_mods_dto.model_dump(), target_keys=None
        )

        # ==========================================
        # ЭТАП 3: Сбор БОНУСОВ МОДИФИКАТОРОВ
        # ==========================================

        self._process_equipment_modifiers(modifiers_pool, equipped_items, base_keys)

        return {"stats": dict(stats_pool), "modifiers": dict(modifiers_pool)}

    # ==================================================
    # Приватные методы обработки (Business Logic Layers)
    # ==================================================

    def _process_base_stats(self, pool: PoolDict, dto: CharacterStatsReadDTO, keys: set[str]):
        """Добавляет 'голые' статы из БД"""
        self._add_layer(pool=pool, source_name="base", data=dto.model_dump(), target_keys=keys)

    def _process_equipment_stats(self, pool: PoolDict, items: ItemList, keys: set[str]):
        """Добавляет бонусы к СТАТАМ от вещей"""
        for item in items:
            self._add_layer(
                pool=pool,
                source_name=item.data.name,
                data=item.data.bonuses,
                target_keys=keys,
            )

    def _process_equipment_modifiers(self, pool: PoolDict, items: ItemList, keys: set[str]):
        """Добавляет бонусы к МОДИФИКАТОРАМ от вещей"""
        for item in items:
            bonuses = item.data.bonuses
            mod_bonuses = {k: v for k, v in bonuses.items() if k not in keys}
            self._add_layer(pool=pool, source_name=item.data.name, data=mod_bonuses, target_keys=None)

    # ==================================================
    # Технические методы (Helpers) - Static
    # ==================================================

    @staticmethod
    def _add_layer(pool: PoolDict, source_name: str, data: dict, target_keys: set[str] | None = None):
        """
        Универсальный "Складыватель".
        """
        for key, value in data.items():
            if target_keys is not None and key not in target_keys:
                continue
            if not isinstance(value, (int, float)):
                continue
            pool[key]["sources"][source_name] = value
            pool[key]["total"] += value

    @staticmethod
    def _create_stats_dto_from_pool(stats_pool: PoolDict, template: CharacterStatsReadDTO) -> CharacterStatsReadDTO:
        """
        Конвертер Dict -> DTO для Калькулятора.
        """
        final_data = template.model_dump()
        for stat_name, stat_data in stats_pool.items():
            if stat_name in final_data:
                final_data[stat_name] = int(stat_data["total"])
        return CharacterStatsReadDTO(**final_data)
