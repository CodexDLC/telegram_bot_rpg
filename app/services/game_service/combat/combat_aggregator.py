# app/services/game_service/combat/combat_aggregator.py
from sqlalchemy.ext.asyncio import AsyncSession

from app.resources.schemas_dto.combat_source_dto import CombatSessionContainerDTO, StatSourceData
from app.services.game_service.modifiers_calculator_service import ModifiersCalculatorService
from database.repositories import get_character_stats_repo, get_inventory_repo


class CombatAggregator:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.stats_repo = get_character_stats_repo(session)
        self.inv_repo = get_inventory_repo(session)

    async def collect_session_container(self, char_id: int) -> CombatSessionContainerDTO:
        container = CombatSessionContainerDTO(char_id=char_id, team="none", name="Unknown")

        # 1. Базовые статы (БД)
        base_stats = await self.stats_repo.get_stats(char_id)
        if base_stats:
            for field in base_stats.model_fields:
                val = getattr(base_stats, field)
                if isinstance(val, (int, float)):
                    if field not in container.stats:
                        container.stats[field] = StatSourceData()
                    container.stats[field].base = float(val)

        # 2. Модификаторы (Формулы Lvl 2)
        # Считаем их на основе базы, чтобы получить стартовые значения крита, хп и т.д.
        if base_stats:
            derived = ModifiersCalculatorService.calculate_all_modifiers_for_stats(base_stats)
            for field in derived.model_fields:
                val = getattr(derived, field)
                if isinstance(val, (int, float)):
                    if field not in container.stats:
                        container.stats[field] = StatSourceData()
                    # Записываем в base, так как это "база" для боя
                    container.stats[field].base = float(val)

        # 3. Экипировка
        items = await self.inv_repo.get_items_by_location(char_id, "equipped")
        for item in items:
            if item.data.bonuses:
                for stat_k, stat_v in item.data.bonuses.items():
                    if stat_k not in container.stats:
                        container.stats[stat_k] = StatSourceData()

                    # Тут логика: если в JSON предмета написано 0.05 -> это %, иначе flat?
                    # Или всегда считать equipment как flat, а % выносить в buffs?
                    # Для простоты пока считаем все бонусы шмота FLAT прибавкой к статам.
                    container.stats[stat_k].equipment += float(stat_v)

        return container
