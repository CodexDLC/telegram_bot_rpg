"""
Модуль содержит правила для расчета производных характеристик (модификаторов)
на основе базовых характеристик персонажа.

СИНХРОНИЗИРОВАНО С: apps/common/schemas_dto/modifier_dto.py
"""

MODIFIER_RULES: dict[str, dict[str, float]] = {
    # ==========================================================================
    # ⚔️ 1. УРОН (Damage Base)
    # ==========================================================================
    # Сила дает чистый урон обеим рукам
    "main_hand_damage_base": {"strength": 1.0},
    "off_hand_damage_base": {"strength": 1.0},
    # Глобальный бонус урона (%)
    "physical_damage_bonus": {"strength": 0.002},
    # ==========================================================================
    # 🎯 2. ТОЧНОСТЬ И ПРОБИТИЕ (Accuracy & Penetration)
    # ==========================================================================
    # Точность для обеих рук
    "main_hand_accuracy": {"perception": 0.02, "agility": 0.005},
    "off_hand_accuracy": {"perception": 0.02, "agility": 0.005},
    # Пробивание брони
    "main_hand_penetration": {"perception": 0.01},
    "off_hand_penetration": {"perception": 0.01},
    # ==========================================================================
    # 💥 3. КРИТ (Crit Chance)
    # ==========================================================================
    "main_hand_crit_chance": {"luck": 0.02},
    "off_hand_crit_chance": {"luck": 0.02},
    # ==========================================================================
    # 🛡️ 4. ЗАЩИТА (Defense)
    # ==========================================================================
    # Уворот
    "dodge_chance": {"agility": 0.02},
    # Анти-Крит (нужно добавить в DTO, если нет)
    # "anti_crit_chance": {"endurance": 0.015, "luck": 0.005},
    # Броня (Flat)
    "damage_reduction_flat": {"endurance": 0.5},
    # Резисты (%)
    "physical_resistance": {"endurance": 0.005},
    # ==========================================================================
    # 🔮 5. МАГИЯ (Magic)
    # ==========================================================================
    "magical_damage_power": {"intelligence": 1.0},
    "magical_accuracy": {"wisdom": 0.02},
    "magical_crit_chance": {"luck": 0.02},  # Пока общий
    "magical_resistance": {"wisdom": 0.01, "men": 0.005},
    # Стихии
    "fire_damage_bonus": {"intelligence": 0.005},
    "water_damage_bonus": {"intelligence": 0.005},
    "air_damage_bonus": {"intelligence": 0.005},
    "earth_damage_bonus": {"intelligence": 0.005},
    "light_damage_bonus": {"intelligence": 0.005},
    "dark_damage_bonus": {"intelligence": 0.005},
    "fire_resistance": {"wisdom": 0.01},
    "water_resistance": {"wisdom": 0.01},
    "air_resistance": {"wisdom": 0.01},
    "earth_resistance": {"wisdom": 0.01},
    "light_resistance": {"wisdom": 0.01},
    "dark_resistance": {"wisdom": 0.01},
    # ==========================================================================
    # 💀 6. СПЕЦ-ЭФФЕКТЫ (Special)
    # ==========================================================================
    "control_resistance": {"men": 0.02},
    "debuff_avoidance": {"men": 0.015},
    "healing_power": {"men": 0.02},
    "energy_max": {"men": 10},
    "energy_regen": {"men": 0.5},
    "thorns_damage_flat": {"endurance": 0.5},
    # Резисты к статусам
    "poison_resistance": {"endurance": 0.02},
    "bleed_resistance": {"endurance": 0.02},
    "shock_resistance": {"endurance": 0.02},
    # ==========================================================================
    # 💰 7. УТИЛИТЫ (Utility)
    # ==========================================================================
    "inventory_slots_bonus": {"perception": 1},
    "weight_limit_bonus": {"strength": 2.0},
    "trade_discount": {"charisma": 0.01},
    "find_loot_chance": {"luck": 0.02},
    "pet_efficiency_mult": {"charisma": 0.03},  # pet_damage/health -> efficiency
}

DEFAULT_VALUES = {
    "dodge_cap": 0.75,
    "resistance_cap": 0.85,
    "shield_block_cap": 0.75,
    "parry_cap": 0.50,
    "counter_attack_cap": 0.50,
    "vampiric_trigger_cap": 1.0,
    "spell_land_chance": 1.0,
}
