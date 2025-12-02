"""
Модуль содержит правила для расчета характеристик персонажа.

Определяет типы агрегации (аддитивная, мультипликативная) для различных
статистик, что позволяет корректно комбинировать бонусы от разных источников.
"""

from enum import StrEnum


class StatCalcType(StrEnum):
    ADDITIVE = "additive"
    MULTIPLICATIVE = "multiplicative"


DEFAULT_CALC_TYPE = StatCalcType.ADDITIVE

STAT_CALCULATION_RULES = {
    "strength": StatCalcType.ADDITIVE,
    "agility": StatCalcType.ADDITIVE,
    "intelligence": StatCalcType.ADDITIVE,
    "endurance": StatCalcType.ADDITIVE,
    "phys_crit_chance": StatCalcType.ADDITIVE,
    "dodge_chance": StatCalcType.ADDITIVE,
    "phys_crit_power": StatCalcType.ADDITIVE,
    "incoming_damage_reduction": StatCalcType.MULTIPLICATIVE,
}
