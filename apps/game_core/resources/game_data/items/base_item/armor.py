"""
РУКОВОДСТВО ПО ЗАПОЛНЕНИЮ: БРОНЯ
================================

Этот файл содержит шаблоны для физической брони (Heavy, Medium, Light).

КЛЮЧЕВЫЕ ПОЛЯ:
---------------
- slot: 'head_armor', 'chest_armor', 'arms_armor', 'legs_armor', 'feet_armor'.
- defense_type: 'physical' (для основной брони) или 'magical' (для брони магов).
- base_power: Показатель защиты (Armor Value).
- implicit_bonuses:
    - Heavy: Штрафы к увороту ('dodge_chance': -0.1), бонусы к сопротивлениям.
    - Medium: Небольшие бонусы к увороту или точности.
    - Light: Бонусы к магии ('magical_resistance', 'energy_regen').
"""

ARMOR_DB = {
    # ==========================================
    # Тяжелая Броня
    # ==========================================
    "heavy_armor": {
        "helmet": {
            "id": "helmet",
            "name_ru": "Шлем",
            "slot": "head_armor",
            "damage_type": None,
            "defense_type": "physical",
            "allowed_materials": ["ingots"],
            "base_power": 5,
            "base_durability": 60,
            "damage_spread": 0.0,
            "narrative_tags": ["helmet", "visor", "protection"],
            "implicit_bonuses": {"anti_crit_chance": 0.05},
        },
        "plate_chest": {
            "id": "plate_chest",
            "name_ru": "Кираса",
            "slot": "chest_armor",
            "damage_type": None,
            "defense_type": "physical",
            "allowed_materials": ["ingots"],
            "base_power": 15,
            "base_durability": 100,
            "damage_spread": 0.0,
            "narrative_tags": ["plate", "heavy", "metal"],
            "implicit_bonuses": {"dodge_chance": -0.10, "physical_resistance": 0.05},
        },
        "gauntlets": {
            "id": "gauntlets",
            "name_ru": "Латные рукавицы",
            "slot": "arms_armor",
            "damage_type": None,
            "defense_type": "physical",
            "allowed_materials": ["ingots"],
            "base_power": 4,
            "base_durability": 70,
            "damage_spread": 0.0,
            "narrative_tags": ["gauntlets", "heavy", "fist"],
            "implicit_bonuses": {"physical_damage_bonus": 0.02},
        },
        "greaves": {
            "id": "greaves",
            "name_ru": "Поножи",
            "slot": "legs_armor",
            "damage_type": None,
            "defense_type": "physical",
            "allowed_materials": ["ingots"],
            "base_power": 6,
            "base_durability": 80,
            "damage_spread": 0.0,
            "narrative_tags": ["greaves", "shin_guard"],
            "implicit_bonuses": {"dodge_chance": -0.05},
        },
        "sabatons": {
            "id": "sabatons",
            "name_ru": "Латные сапоги",
            "slot": "feet_armor",
            "damage_type": None,
            "defense_type": "physical",
            "allowed_materials": ["ingots"],
            "base_power": 4,
            "base_durability": 70,
            "damage_spread": 0.0,
            "narrative_tags": ["sabatons", "heavy_boots"],
            "implicit_bonuses": {"physical_resistance": 0.02},
        },
    },
    # ==========================================
    # Средняя Броня
    # ==========================================
    "medium_armor": {
        "leather_cap": {
            "id": "leather_cap",
            "name_ru": "Кожаный шлем",
            "slot": "head_armor",
            "damage_type": None,
            "defense_type": "physical",
            "allowed_materials": ["leathers"],
            "base_power": 3,
            "base_durability": 40,
            "damage_spread": 0.0,
            "narrative_tags": ["cap", "leather"],
            "implicit_bonuses": {},
        },
        "jerkin": {
            "id": "jerkin",
            "name_ru": "Куртка",
            "slot": "chest_armor",
            "damage_type": None,
            "defense_type": "physical",
            "allowed_materials": ["leathers"],
            "base_power": 8,
            "base_durability": 60,
            "damage_spread": 0.0,
            "narrative_tags": ["jacket", "vest", "scout"],
            "implicit_bonuses": {"dodge_chance": 0.02},
        },
        "bracers": {
            "id": "bracers",
            "name_ru": "Наручи",
            "slot": "arms_armor",
            "damage_type": None,
            "defense_type": "physical",
            "allowed_materials": ["leathers"],
            "base_power": 2,
            "base_durability": 45,
            "damage_spread": 0.0,
            "narrative_tags": ["bracers", "wrist_guard"],
            "implicit_bonuses": {"physical_accuracy": 0.02},
        },
        "breeches": {
            "id": "breeches",
            "name_ru": "Штаны",
            "slot": "legs_armor",
            "damage_type": None,
            "defense_type": "physical",
            "allowed_materials": ["leathers"],
            "base_power": 4,
            "base_durability": 50,
            "damage_spread": 0.0,
            "narrative_tags": ["pants", "leather"],
            "implicit_bonuses": {},
        },
        "boots": {
            "id": "boots",
            "name_ru": "Сапоги",
            "slot": "feet_armor",
            "damage_type": None,
            "defense_type": "physical",
            "allowed_materials": ["leathers"],
            "base_power": 3,
            "base_durability": 50,
            "damage_spread": 0.0,
            "narrative_tags": ["boots", "travel"],
            "implicit_bonuses": {"dodge_chance": 0.03},
        },
    },
    # ==========================================
    # Легкая Броня
    # ==========================================
    "light_armor": {
        "hood": {
            "id": "hood",
            "name_ru": "Капюшон",
            "slot": "head_armor",
            "damage_type": None,
            "defense_type": "magical",
            "allowed_materials": ["cloths"],
            "base_power": 1,
            "base_durability": 30,
            "damage_spread": 0.0,
            "narrative_tags": ["hood", "mage_hat"],
            "implicit_bonuses": {"magical_resistance": 0.05},
        },
        "robe": {
            "id": "robe",
            "name_ru": "Мантия",
            "slot": "chest_armor",
            "damage_type": None,
            "defense_type": "magical",
            "allowed_materials": ["cloths"],
            "base_power": 4,
            "base_durability": 40,
            "damage_spread": 0.0,
            "narrative_tags": ["robe", "wizard", "cloth"],
            "implicit_bonuses": {"magical_resistance": 0.10, "energy_regen": 1.0},
        },
        "wraps": {
            "id": "wraps",
            "name_ru": "Обмотки",
            "slot": "arms_armor",
            "damage_type": None,
            "defense_type": "magical",
            "allowed_materials": ["cloths"],
            "base_power": 1,
            "base_durability": 25,
            "damage_spread": 0.0,
            "narrative_tags": ["wraps", "bandages"],
            "implicit_bonuses": {"energy_regen": 0.2},
        },
        "leggings": {
            "id": "leggings",
            "name_ru": "Леггинсы",
            "slot": "legs_armor",
            "damage_type": None,
            "defense_type": "magical",
            "allowed_materials": ["cloths"],
            "base_power": 2,
            "base_durability": 30,
            "damage_spread": 0.0,
            "narrative_tags": ["leggings", "cloth"],
            "implicit_bonuses": {"magical_resistance": 0.03},
        },
        "sandals": {
            "id": "sandals",
            "name_ru": "Сандалии",
            "slot": "feet_armor",
            "damage_type": None,
            "defense_type": "magical",
            "allowed_materials": ["cloths", "leathers"],
            "base_power": 1,
            "base_durability": 25,
            "damage_spread": 0.0,
            "narrative_tags": ["sandals", "light_footwear"],
            "implicit_bonuses": {"dodge_chance": 0.01},
        },
    },
}
