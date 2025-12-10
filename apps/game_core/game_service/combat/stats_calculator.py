from loguru import logger as log

from apps.common.schemas_dto import StatSourceData
from apps.game_core.resources.game_data.stats_rules import DEFAULT_CALC_TYPE, STAT_CALCULATION_RULES, StatCalcType


class StatsCalculator:
    """
    Сервис для расчета итоговых значений характеристик из различных источников.

    Преобразует `StatSourceData` в конкретное числовое значение (float),
    применяя правила агрегации, определенные в `STAT_CALCULATION_RULES`.
    """

    @staticmethod
    def calculate(stat_key: str, source: StatSourceData) -> float:
        """
        Рассчитывает итоговое значение одной характеристики.

        Args:
            stat_key: Ключ характеристики (например, "physical_damage_bonus").
            source: Объект `StatSourceData`, содержащий базовые значения,
                    бонусы от экипировки, навыков и баффов.

        Returns:
            Итоговое значение характеристики в виде float.
        """
        calc_type = STAT_CALCULATION_RULES.get(stat_key, DEFAULT_CALC_TYPE)

        flat_total = source.base + source.equipment + source.skills + sum(source.buffs_flat.values())
        percent_sum = sum(source.buffs_percent.values())
        final_value: float = flat_total

        if calc_type == StatCalcType.ADDITIVE:
            final_value = flat_total * (1.0 + percent_sum)
            log.trace(
                f"StatsCalculator | type=ADDITIVE stat='{stat_key}' flat={flat_total} percent_sum={percent_sum} final={final_value}"
            )
        elif calc_type == StatCalcType.MULTIPLICATIVE:
            multiplier = 1.0
            for _p_key, p_val in source.buffs_percent.items():  # Changed p_key to _p_key
                multiplier *= 1.0 + p_val
            final_value = flat_total * multiplier
            log.trace(
                f"StatsCalculator | type=MULTIPLICATIVE stat='{stat_key}' flat={flat_total} multiplier={multiplier} final={final_value}"
            )
        else:  # StatCalcType.FLAT
            log.trace(f"StatsCalculator | type=FLAT stat='{stat_key}' final={final_value}")

        return final_value

    @staticmethod
    def aggregate_all(stats_map: dict[str, StatSourceData]) -> dict[str, float]:
        """
        Проходит по всему словарю характеристик и рассчитывает их итоговые значения.

        Args:
            stats_map: Словарь, где ключ — название характеристики,
                       а значение — объект `StatSourceData`.

        Returns:
            Словарь, где ключ — название характеристики, а значение — её итоговое float-значение.
        """
        result = {}
        log.debug(f"StatsCalculator | action=aggregate_all stats_count={len(stats_map)}")
        for key, data in stats_map.items():
            result[key] = StatsCalculator.calculate(key, data)
        return result
