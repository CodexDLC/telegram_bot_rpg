# app/resources/game_data/stats_rules.py
from enum import StrEnum


class StatCalcType(StrEnum):
    ADDITIVE = "additive"  # (Base + Equip + Buffs) * (1 + Multipliers)
    MULTIPLICATIVE = "multiplicative"  # Base * (1+Equip) * (1+Buff) * ...
    # Можно добавить DIMINISHING для брони в будущем


# Правила по умолчанию: Если стата нет в списке — считаем ADDITIVE
DEFAULT_CALC_TYPE = StatCalcType.ADDITIVE

# Реестр правил для каждого ключа
STAT_CALCULATION_RULES = {
    # --- ПЕРВИЧНЫЕ (Просто сумма) ---
    "strength": StatCalcType.ADDITIVE,
    "agility": StatCalcType.ADDITIVE,
    "intelligence": StatCalcType.ADDITIVE,
    "endurance": StatCalcType.ADDITIVE,
    # --- БОЕВЫЕ % (Сумма %, затем множители) ---
    "phys_crit_chance": StatCalcType.ADDITIVE,  # 5% + 10% = 15%
    "dodge_chance": StatCalcType.ADDITIVE,
    # --- СЛОЖНЫЕ (Перемножение) ---
    # Например, урон: (Base) * (1.15 от меча) * (1.5 от крита)
    # Или если мы решим, что 'crit_power' это множитель (x1.5), а не % (+50%)
    "phys_crit_power": StatCalcType.ADDITIVE,  # Обычно база 1.5 + 0.1 + 0.2 = 1.8
    # Пример чистого множителя
    "incoming_damage_reduction": StatCalcType.MULTIPLICATIVE,
}
