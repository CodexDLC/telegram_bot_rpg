"""
Модуль содержит правила для расчета производных характеристик (модификаторов)
на основе базовых характеристик персонажа.

Определяет, как каждая базовая характеристика влияет на различные
модификаторы (например, урон, сопротивления, шансы), а также
предоставляет значения по умолчанию для некоторых модификаторов.
"""

MODIFIER_RULES = {
    "physical_damage_bonus": {"strength": 0.025},
    "physical_penetration": {"strength": 0.01},
    "physical_crit_chance": {"agility": 0.01},
    "dodge_chance": {"agility": 0.01},
    "anti_dodge_chance": {"agility": 0.01},
    "shield_block_chance": {"agility": 0.01},
    "magical_damage_bonus": {"intelligence": 0.025},
    "magical_penetration": {"intelligence": 0.01},
    "spell_land_chance": {"intelligence": 0.01},
    "magical_crit_chance": {"wisdom": 0.015},
    "magical_accuracy": {"wisdom": 0.015},
    "debuff_avoidance": {"wisdom": 0.015},
    "hp_max": {"endurance": 15},
    "physical_resistance": {"endurance": 0.01},
    "shock_resistance": {"endurance": 0.01},
    "energy_max": {"men": 10},
    "energy_regen": {"men": 0.05},
    "magical_resistance": {"men": 0.01},
    "control_resistance": {"men": 0.015},
    "trade_discount": {"luck": 0.015},
    "find_loot_chance": {"luck": 0.015},
    "crafting_critical_chance": {"luck": 0.01},
    "crafting_success_chance": {"luck": 0.015},
    "skill_gain_bonus": {"luck": 0.02},
    "pet_damage_bonus": {"luck": 0.025, "charisma": 0.01},
    "inventory_slots_bonus": {"perception": 1},
}

DEFAULT_VALUES = {
    "physical_crit_cap": 0.75,
    "physical_crit_power_float": 1.5,
    "magical_crit_cap": 0.75,
    "magical_crit_power_float": 1.5,
    "spell_land_chance": 1.0,
    "shield_block_power": 0.0,
}
