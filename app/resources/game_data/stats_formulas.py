# app/resources/game_data/stats_formulas.py

# Формат: "поле_в_dto_модификаторов": {"стат_персонажа": множитель}
# Pydantic сам приведет типы (int/float), если результат будет 150.0 для int поля.

MODIFIER_RULES = {
    # ==========================================
    # 1. Физические Боевые (Strength / Agility)
    # ==========================================
    "physical_damage_bonus": {"strength": 0.025},
    "physical_penetration": {"strength": 0.01},
    "physical_crit_chance": {"agility": 0.01},
    "dodge_chance": {"agility": 0.01},
    "anti_dodge": {"agility": 0.01},
    "shield_block_chance": {"agility": 0.01},
    # ==========================================
    # 2. Магические Боевые (Intelligence / Wisdom)
    # ==========================================
    # Интеллект — это "Сила" магии (Power)
    "magical_damage_bonus": {"intelligence": 0.025},
    "magical_penetration": {"intelligence": 0.01},
    "spell_land_chance": {"intelligence": 0.01},  # Шанс пробить резист
    # Мудрость (Wisdom) — это "Ловкость" магии (Finesse)
    # (Твой запрос на аналог Agility)
    "magical_crit_chance": {"wisdom": 0.015},  # Магический крит
    "magical_accuracy": {"wisdom": 0.015},  # Магическая точность
    "debuff_avoidance": {"wisdom": 0.015},  # Магическое уклонение
    # ==========================================
    # 3. Ресурсы и Защита (Endurance / Men)
    # ==========================================
    # Выносливость — Физическое тело
    "hp_max": {"endurance": 15},
    "hp_regen": {"endurance": 0.02},
    "physical_resistance": {"endurance": 0.01},
    "shock_resistance": {"endurance": 0.01},
    # Дух (Men) — Ментальное тело
    "energy_max": {"men": 10},
    "energy_regen": {"men": 0.05},
    "magical_resistance": {"men": 0.01},
    "control_resistance": {"men": 0.015},
    # ==========================================
    # 4. Утилиты (Luck / Perception)
    # ==========================================
    "trade_discount": {"luck": 0.015},
    "find_loot_chance": {"luck": 0.015},
    "crafting_critical_chance": {"luck": 0.01},
    "crafting_success_chance": {"luck": 0.015},
    "skill_gain_bonus": {"luck": 0.02},
    # Бонус питомцам тоже можно привязать к Удаче или Харизме
    "pet_ally_power": {"luck": 0.025, "charisma": 0.01},  # Пример смешанного стата!
    "inventory_slots_bonus": {"perception": 1},
}

# Значения по умолчанию для полей, которые не зависят от статов
# (Чтобы не хардкодить их в коде сервиса)
DEFAULT_VALUES = {
    "physical_crit_chance_cap": 0.75,
    "physical_crit_power_float": 1.5,
    "magical_crit_chance_cap": 0.75,
    "magical_crit_power_float": 1.5,
    "spell_land_chance": 1.0,
    "shield_block_power": 0.0,
}
