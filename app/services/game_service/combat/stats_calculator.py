# app/services/game_service/combat/stats_calculator.py
from app.resources.game_data.stats_rules import DEFAULT_CALC_TYPE, STAT_CALCULATION_RULES, StatCalcType
from app.resources.schemas_dto.combat_source_dto import StatSourceData


class StatsCalculator:
    """
    Превращает StatSourceData в конкретное число (float).
    """

    @staticmethod
    def calculate(stat_key: str, source: StatSourceData) -> float:
        # 1. Определяем стратегию расчета
        calc_type = STAT_CALCULATION_RULES.get(stat_key, DEFAULT_CALC_TYPE)

        # 2. Считаем "Плоскую" часть (Flat)
        # Base + Equip + Skills + Flat Buffs
        flat_total = source.base + source.equipment + source.skills + sum(source.buffs_flat.values())

        # 3. Считаем "Процентную" часть
        # Тут логика может отличаться в зависимости от типа

        if calc_type == StatCalcType.ADDITIVE:
            # Формула: Flat * (1 + Sum(Percents))
            # Пример: Сила 100 + (10% аура + 5% зелье) = 100 * 1.15 = 115
            percent_sum = sum(source.buffs_percent.values())
            final_value = flat_total * (1.0 + percent_sum)
            return final_value

        elif calc_type == StatCalcType.MULTIPLICATIVE:
            # Формула: Flat * (1+P1) * (1+P2) * ...
            # Пример: Снижение урона. (1 - 0.1) * (1 - 0.2) ...
            multiplier = 1.0
            for p_val in source.buffs_percent.values():
                multiplier *= 1.0 + p_val

            final_value = flat_total * multiplier
            return final_value

        return flat_total

    @staticmethod
    def aggregate_all(stats_map: dict[str, StatSourceData]) -> dict[str, float]:
        """
        Проходит по всему словарю статов и считает итоги.
        """
        result = {}
        for key, data in stats_map.items():
            result[key] = StatsCalculator.calculate(key, data)
        return result
