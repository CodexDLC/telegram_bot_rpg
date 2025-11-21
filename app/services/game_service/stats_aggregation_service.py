from collections import defaultdict
from typing import TypedDict

from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from app.resources.schemas_dto.character_dto import CharacterStatsReadDTO
from app.resources.schemas_dto.item_dto import InventoryItemDTO, ItemType
from app.services.game_service.modifiers_calculator_service import ModifiersCalculatorService
from database.repositories import get_character_stats_repo, get_inventory_repo


# Определяем строгую структуру
class StatInfo(TypedDict):
    total: int | float
    sources: dict[str, int | float]


# Список ОБЕРТОК инвентаря (InventoryItemDTO)
ItemList = list[InventoryItemDTO]
PoolDict = dict[str, StatInfo]


class StatsAggregationService:
    """
    Сервис-Агрегатор.
    Оркестрирует сбор характеристик из всех источников.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.stats_repo = get_character_stats_repo(session)
        self.inv_repo = get_inventory_repo(session)

    async def get_character_total_stats(self, char_id: int) -> dict[str, PoolDict]:
        log.debug(f"Начало агрегации статов для char_id={char_id}")

        def factory() -> StatInfo:
            return {"total": 0, "sources": {}}

        # Указываем типы для mypy
        stats_pool: defaultdict[str, StatInfo] = defaultdict(factory)
        modifiers_pool: defaultdict[str, StatInfo] = defaultdict(factory)

        # 1. Загрузка данных
        base_stats_dto = await self.stats_repo.get_stats(char_id)
        if not base_stats_dto:
            log.error(f"Базовые статы не найдены для char_id={char_id}")
            return {}

        # Получаем предметы (это список InventoryItemDTO)
        equipped_items: ItemList = await self.inv_repo.get_items_by_location(char_id, "equipped")

        base_keys = set(CharacterStatsReadDTO.model_fields.keys())

        # ==========================================
        # ЭТАП 1: Сбор ПЕРВИЧНЫХ ХАРАКТЕРИСТИК
        # ==========================================
        self._process_base_stats(stats_pool, base_stats_dto, base_keys)
        self._process_equipment_stats(stats_pool, equipped_items, base_keys)

        # ==========================================
        # ЭТАП 2: Расчет ПРОИЗВОДНЫХ
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

        # Превращаем defaultdict в обычный dict перед возвратом
        return {"stats": dict(stats_pool), "modifiers": dict(modifiers_pool)}

    # ==================================================
    # Приватные методы обработки
    # ==================================================

    def _process_base_stats(self, pool: PoolDict, dto: CharacterStatsReadDTO, keys: set[str]):
        """Добавляет 'голые' статы из БД"""
        self._add_layer(pool=pool, source_name="base", data=dto.model_dump(), target_keys=keys)

    def _process_equipment_stats(self, pool: PoolDict, items: ItemList, keys: set[str]):
        """Добавляет бонусы к ПЕРВИЧНЫМ СТАТАМ от вещей"""
        for item in items:
            # ИСПРАВЛЕНО: проверка типа напрямую, а не через .item
            if item.item_type == ItemType.CONSUMABLE:
                continue

            # ИСПРАВЛЕНО: Вычисляем полные бонусы (база + аффиксы) через хелпер
            bonuses = self._extract_total_bonuses(item)

            # ИСПРАВЛЕНО: Имя берем из .data
            item_name = item.data.name

            self._add_layer(
                pool=pool,
                source_name=item_name,
                data=bonuses,
                target_keys=keys,
            )

    def _process_equipment_modifiers(self, pool: PoolDict, items: ItemList, keys: set[str]):
        """Добавляет бонусы к МОДИФИКАТОРАМ (Crit, Dmg...) от вещей"""
        for item in items:
            if item.item_type == ItemType.CONSUMABLE:
                continue

            bonuses = self._extract_total_bonuses(item)
            item_name = item.data.name

            # Берем только то, чего НЕТ в списке первичных статов
            mod_bonuses = {k: v for k, v in bonuses.items() if k not in keys}

            self._add_layer(pool=pool, source_name=item_name, data=mod_bonuses, target_keys=None)

    # ==================================================
    # Технические методы (Helpers)
    # ==================================================

    @staticmethod
    def _extract_total_bonuses(item: InventoryItemDTO) -> dict[str, int | float]:
        """
        Извлекает все бонусы предмета.
        Объединяет случайные аффиксы (bonuses) и базовые свойства (protection, damage).
        """
        # Копируем словарь бонусов, чтобы не менять исходный объект
        # data всегда есть, но mypy нужно знать, что это не Consumable (мы это проверяем выше, но здесь безопаснее явно)
        if item.item_type == ItemType.CONSUMABLE:
            return {}

        # Берем словарь аффиксов (сила +5 и т.д.)
        # .data есть у всех типов в Union, кроме, теоретически, ошибок валидации, но Pydantic это гарантирует
        total = item.data.bonuses.copy()

        # Добавляем специфичные для типа статы
        if item.item_type == ItemType.WEAPON:
            # mypy здесь поймет, что item - это WeaponItemDTO, и у data есть damage_min
            # Предполагаем, что для статов берем средний урон или макс?
            # Обычно в статы агрегируется "Weapon Damage" или типа того.
            # Если в игре есть стат "damage", добавляем его:
            # total["physical_damage"] = item.data.damage_max (пример)
            pass

        elif item.item_type == ItemType.ARMOR:
            # Добавляем броню в общие статы
            if item.data.protection:
                # Если у тебя есть стат "protection" или "armor"
                current_armor = total.get("protection", 0)
                total["protection"] = current_armor + item.data.protection

            # Если есть штраф к мобильности (отрицательный бонус)
            if item.data.mobility_penalty:
                # Предполагаем, что это нужно вычесть из чего-то или добавить как штраф
                pass

        return total

    @staticmethod
    def _add_layer(pool: PoolDict, source_name: str, data: dict, target_keys: set[str] | None = None):
        for key, value in data.items():
            if target_keys is not None and key not in target_keys:
                continue

            # Проверка типа (защита от мусора и нулей, если нужно строго число)
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
