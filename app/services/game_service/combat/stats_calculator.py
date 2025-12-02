# app/services/game_service/combat/stats_calculator.py

from loguru import logger as log

from app.resources.game_data.stats_rules import DEFAULT_CALC_TYPE, STAT_CALCULATION_RULES, StatCalcType
from app.resources.schemas_dto.combat_source_dto import StatSourceData


class StatsCalculator:
    """
    Превращает StatSourceData в конкретное число (float).
    """

    @staticmethod
    def calculate(stat_key: str, source: StatSourceData) -> float:
        """
        Рассчитывает итоговое значение одного стата.

        Args:
            stat_key: Ключ стата (e.g., "physical_damage_bonus").
            source: Источник данных стата.

        Returns:
            Итоговое значение.
        """
        # 1. Определяем стратегию расчета
        calc_type = STAT_CALCULATION_RULES.get(stat_key, DEFAULT_CALC_TYPE)

        # 2. Считаем "Плоскую" часть (Flat)
        # Base + Equip + Skills + Flat Buffs
        flat_total = source.base + source.equipment + source.skills + sum(source.buffs_flat.values())

        # 3. Считаем "Процентную" часть
        percent_sum = sum(source.buffs_percent.values())
        final_value: float = flat_total

        if calc_type == StatCalcType.ADDITIVE:
            # Формула: Flat * (1 + Sum(Percents))
            # Пример: Сила 100 + (10% аура + 5% зелье) = 100 * 1.15 = 115
            final_value = flat_total * (1.0 + percent_sum)
            log.trace(
                f"StatCalcAdditive | stat={stat_key} flat_total={flat_total} percent_sum={percent_sum} final_value={final_value}"
            )

        elif calc_type == StatCalcType.MULTIPLICATIVE:
            # Формула: Flat * (1+P1) * (1+P2) * ...
            # Пример: Снижение урона. (1 - 0.1) * (1 - 0.2) ...
            multiplier = 1.0
            for p_key, p_val in source.buffs_percent.items():
                multiplier *= 1.0 + p_val
                log.trace(
                    f"StatCalcMultiplicativeStep | stat={stat_key} buff_key={p_key} p_val={p_val} current_multiplier={multiplier}"
                )

            final_value = flat_total * multiplier
            log.trace(
                f"StatCalcMultiplicative | stat={stat_key} flat_total={flat_total} final_multiplier={multiplier} final_value={final_value}"
            )

        else:  # StatCalcType.FLAT
            log.trace(f"StatCalcFlat | stat={stat_key} final_value={final_value}")

        return final_value

    @staticmethod
    def aggregate_all(stats_map: dict[str, StatSourceData]) -> dict[str, float]:
        """
        Проходит по всему словарю статов и считает итоги.

        Args:
            stats_map: Словарь источников данных статов.

        Returns:
            Словарь с итоговыми значениями статов.
        """
        result = {}
        log.debug(f"AggregatingAllStats | stats_count={len(stats_map)}")
        for key, data in stats_map.items():
            result[key] = StatsCalculator.calculate(key, data)
        return result
