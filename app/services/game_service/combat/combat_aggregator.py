from sqlalchemy.ext.asyncio import AsyncSession

from app.resources.schemas_dto.combat_source_dto import CombatComplexStatsDTO
from app.resources.schemas_dto.item_dto import ItemType
from app.services.game_service.modifiers_calculator_service import ModifiersCalculatorService
from database.repositories import get_character_stats_repo, get_inventory_repo


class CombatAggregator:
    """
    Специализированный сборщик данных для инициализации БОЯ.
    Собирает данные в структуру с источниками (Base, Equipment, Skills).
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.stats_repo = get_character_stats_repo(session)
        self.inv_repo = get_inventory_repo(session)

    async def collect_complex_stats(self, char_id: int) -> CombatComplexStatsDTO:
        """
        Собирает полную структуру статов с источниками.
        """
        # Инициализируем пустую структуру
        complex_stats = CombatComplexStatsDTO()

        # 1. БАЗОВЫЕ СТАТЫ (Из БД)
        base_stats_dto = await self.stats_repo.get_stats(char_id)
        if base_stats_dto:
            # Заполняем поле 'base' для каждого стата
            # Важно: имена полей в DTO должны совпадать
            for stat in [
                "strength",
                "agility",
                "endurance",
                "intelligence",
                "wisdom",
                "men",
                "perception",
                "charisma",
                "luck",
            ]:
                val = getattr(base_stats_dto, stat, 0)
                if hasattr(complex_stats, stat):
                    getattr(complex_stats, stat).base = val

        # 2. ЭКИПИРОВКА (Из Инвентаря)
        equipped_items = await self.inv_repo.get_items_by_location(char_id, "equipped")

        # Карта слотов для брони (куда писать бонус защиты)
        armor_slot_map = {
            "head": "armor_head",
            "chest": "armor_chest",
            "body": "armor_chest",  # Иногда body = chest
            "legs": "armor_legs",
            "feet": "armor_feet",
        }

        for item in equipped_items:
            # А. Бонусы к статам (+5 Str, +2 Crit)
            # item.data.bonuses - это словарь {"strength": 5, "crit_chance": 2}
            if item.data.bonuses:
                for stat_key, val in item.data.bonuses.items():
                    # Маппинг имен (если в item_data они отличаются от DTO)
                    # Например, в items мб 'physical_crit_chance', а в DTO 'phys_crit_chance'
                    # Пока считаем, что они совпадают или мы их приведем к общему виду
                    target_key = stat_key

                    if hasattr(complex_stats, target_key):
                        # Прибавляем к источнику 'equipment'
                        getattr(complex_stats, target_key).equipment += int(val)

            # Б. Броня (Protection -> Armor Zone)
            if item.item_type == ItemType.ARMOR:
                protection = getattr(item.data, "protection", 0)
                # Если у нас механика 1d6, то тут будет парсинг строки?
                # Пока для ComplexStats мы храним INT (суммарный бонус защиты).
                # Если мы хотим хранить формулы, StatSourcesDTO должен быть generic, но это усложнит.
                # Для MVP: если protection это число, пишем в equipment.
                if isinstance(protection, int) and protection > 0:
                    for slot in item.data.valid_slots:
                        target_field = armor_slot_map.get(slot)
                        if target_field and hasattr(complex_stats, target_field):
                            getattr(complex_stats, target_field).equipment += protection

            # В. Урон Оружия
            if item.item_type == ItemType.WEAPON:
                dmg_min = getattr(item.data, "damage_min", 0)
                dmg_max = getattr(item.data, "damage_max", 0)

                complex_stats.phys_damage_min.equipment += dmg_min
                complex_stats.phys_damage_max.equipment += dmg_max

        # 3. КАЛЬКУЛЯТОР МОДИФИКАТОРОВ (Base Stats -> Derived Base)
        # Нам нужно рассчитать производные (например, Crit из Agility),
        # но записать их в 'base' соответствующего модификатора.

        if base_stats_dto:
            # Используем старый сервис, чтобы получить значения формул
            calc_result = ModifiersCalculatorService.calculate_all_modifiers_for_stats(base_stats_dto)

            # Переносим результаты в 'base' наших сложных статов
            # (Приводим float к int, если нужно, или умножаем на 100 для %)
            complex_stats.phys_crit_chance.base = int(calc_result.physical_crit_chance * 100)  # 0.05 -> 5
            complex_stats.dodge_chance.base = int(calc_result.dodge_chance * 100)
            complex_stats.hp_max.base = int(
                calc_result.hp_max
            )  # HP Max обычно не имеет источников в бою, но можно добавить

            # Природная броня
            complex_stats.armor_natural.base = int(calc_result.physical_resistance * 100)  # Если резист %

        return complex_stats
