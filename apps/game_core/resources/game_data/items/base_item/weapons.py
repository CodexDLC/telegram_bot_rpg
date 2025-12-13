"""
РУКОВОДСТВО ПО ЗАПОЛНЕНИЮ: ОРУЖИЕ И ЩИТЫ
=========================================

Этот файл содержит шаблоны для оружия и щитов.

КЛАССИФИКАЦИЯ ПО СЛОТАМ:
--------------------------
- slot: Основной слот ('main_hand', 'two_hand', 'off_hand').
- extra_slots: Список доп. слотов. Например, для кинжала:
    - slot: 'main_hand'
    - extra_slots: ['off_hand']
  Это позволит носить его в любой руке.

КЛЮЧЕВЫЕ ПОЛЯ:
---------------
- base_power: Средний урон (для оружия) или показатель защиты (для щитов).
- damage_spread: Разброс урона в % (0.1 = +/- 10%).
- implicit_bonuses: Врожденные бонусы (точность, крит, парирование).
"""

WEAPONS_DB = {
    # ==========================================
    # 1. ЛЕГКОЕ ОДНОРУЧНОЕ (Main Hand / Off Hand)
    # ==========================================
    "light_1h": {
        "dagger": {
            "id": "dagger",
            "name_ru": "Кинжал",
            "slot": "main_hand",
            "extra_slots": ["off_hand"],
            "damage_type": "physical",
            "defense_type": None,
            "allowed_materials": ["ingots"],
            "base_power": 6,
            "damage_spread": 0.05,
            "base_durability": 40,
            "narrative_tags": ["dagger", "swift", "stealth"],
            "implicit_bonuses": {
                "dodge_chance": 0.05,
                "physical_crit_chance": 0.20,
                "physical_crit_power_float": 1.0,
                "physical_accuracy": 0.15,
            },
        },
        "hatchet": {
            "id": "hatchet",
            "name_ru": "Топорик",
            "slot": "main_hand",
            "extra_slots": ["off_hand"],
            "damage_type": "physical",
            "defense_type": None,
            "allowed_materials": ["ingots"],
            "base_power": 7,
            "damage_spread": 0.3,
            "base_durability": 50,
            "narrative_tags": ["axe", "light", "chop"],
            "implicit_bonuses": {
                "physical_crit_chance": 0.15,
                "physical_crit_power_float": 0.60,
            },
        },
        "wakizashi": {
            "id": "wakizashi",
            "name_ru": "Вакидзаси",
            "slot": "main_hand",
            "extra_slots": ["off_hand"],
            "damage_type": "physical",
            "defense_type": None,
            "allowed_materials": ["ingots"],
            "base_power": 8,
            "damage_spread": 0.1,
            "base_durability": 55,
            "narrative_tags": ["wakizashi", "samurai", "blade"],
            "implicit_bonuses": {
                "bleed_damage_bonus": 0.1,
                "physical_accuracy": 0.10,
            },
        },
    },
    # ==========================================
    # 2. СРЕДНЕЕ ОДНОРУЧНОЕ (Main Hand Only)
    # ==========================================
    "medium_1h": {
        "sword": {
            "id": "sword",
            "name_ru": "Меч",
            "slot": "main_hand",
            "damage_type": "physical",
            "defense_type": None,
            "allowed_materials": ["ingots"],
            "base_power": 10,
            "damage_spread": 0.1,
            "base_durability": 60,
            "narrative_tags": ["sword", "balanced", "blade"],
            "implicit_bonuses": {
                "physical_accuracy": 0.10,
                "parry_chance": 0.05,
            },
        },
        "battle_axe": {
            "id": "battle_axe",
            "name_ru": "Боевой топор",
            "slot": "main_hand",
            "damage_type": "physical",
            "defense_type": None,
            "allowed_materials": ["ingots"],
            "base_power": 12,
            "damage_spread": 0.4,
            "base_durability": 50,
            "narrative_tags": ["axe", "brutal", "chop"],
            "implicit_bonuses": {
                "physical_accuracy": -0.05,
                "physical_crit_chance": 0.25,
                "physical_crit_power_float": 0.80,
            },
        },
        "mace": {
            "id": "mace",
            "name_ru": "Булава",
            "slot": "main_hand",
            "damage_type": "physical",
            "defense_type": None,
            "allowed_materials": ["ingots"],
            "base_power": 11,
            "damage_spread": 0.2,
            "base_durability": 80,
            "narrative_tags": ["mace", "crushing", "blunt"],
            "implicit_bonuses": {"physical_penetration": 0.20},
        },
        "rapier": {
            "id": "rapier",
            "name_ru": "Рапира",
            "slot": "main_hand",
            "damage_type": "physical",
            "defense_type": None,
            "allowed_materials": ["ingots"],
            "base_power": 8,
            "damage_spread": 0.05,
            "base_durability": 45,
            "narrative_tags": ["rapier", "fencing", "piercing"],
            "implicit_bonuses": {
                "physical_penetration": 0.30,
                "physical_accuracy": 0.15,
            },
        },
    },
    # ==========================================
    # 3. ДВУРУЧНОЕ ОРУЖИЕ (Two Hand)
    # ==========================================
    "melee_2h": {
        "greatsword": {
            "id": "greatsword",
            "name_ru": "Клеймор",
            "slot": "two_hand",
            "damage_type": "physical",
            "defense_type": None,
            "allowed_materials": ["ingots"],
            "base_power": 20,
            "damage_spread": 0.15,
            "base_durability": 70,
            "narrative_tags": ["greatsword", "massive", "cleave"],
            "implicit_bonuses": {
                "parry_chance": 0.15,
                "physical_damage_bonus": 0.10,
            },
        },
        "warhammer": {
            "id": "warhammer",
            "name_ru": "Боевой Молот",
            "slot": "two_hand",
            "damage_type": "physical",
            "defense_type": None,
            "allowed_materials": ["ingots"],
            "base_power": 24,
            "damage_spread": 0.3,
            "base_durability": 90,
            "narrative_tags": ["hammer", "smash", "heavy"],
            "implicit_bonuses": {
                "physical_penetration": 0.40,
                "dodge_chance": -0.15,
            },
        },
        "spear": {
            "id": "spear",
            "name_ru": "Копье",
            "slot": "two_hand",
            "damage_type": "physical",
            "defense_type": None,
            "allowed_materials": ["ingots", "woods"],
            "base_power": 18,
            "damage_spread": 0.1,
            "base_durability": 50,
            "narrative_tags": ["spear", "reach", "piercing"],
            "implicit_bonuses": {
                "counter_attack_chance": 0.20,
                "physical_accuracy": 0.10,
            },
        },
        "katana": {
            "id": "katana",
            "name_ru": "Катана",
            "slot": "two_hand",
            "damage_type": "physical",
            "defense_type": None,
            "allowed_materials": ["ingots"],
            "base_power": 19,
            "damage_spread": 0.1,
            "base_durability": 65,
            "narrative_tags": ["katana", "samurai", "fast_blade"],
            "implicit_bonuses": {
                "physical_crit_chance": 0.15,
                "bleed_damage_bonus": 0.15,
                "parry_chance": 0.10,
            },
        },
        "quarterstaff": {
            "id": "quarterstaff",
            "name_ru": "Боевой посох",
            "slot": "two_hand",
            "damage_type": "physical",
            "defense_type": "physical",
            "allowed_materials": ["woods"],
            "base_power": 12,
            "damage_spread": 0.1,
            "base_durability": 100,
            "narrative_tags": ["staff", "monk", "defensive"],
            "implicit_bonuses": {
                "parry_chance": 0.25,
                "dodge_chance": 0.05,
            },
        },
    },
    # ==========================================
    # 4. ДАЛЬНИЙ БОЙ (Ranged)
    # ==========================================
    "ranged": {
        "shortbow": {
            "id": "shortbow",
            "name_ru": "Короткий лук",
            "slot": "two_hand",
            "damage_type": "physical",
            "defense_type": None,
            "allowed_materials": ["woods"],
            "base_power": 12,
            "damage_spread": 0.1,
            "base_durability": 40,
            "narrative_tags": ["bow", "ranger", "fast"],
            "implicit_bonuses": {"physical_accuracy": 0.20},
        },
        "longbow": {
            "id": "longbow",
            "name_ru": "Длинный лук",
            "slot": "two_hand",
            "damage_type": "physical",
            "defense_type": None,
            "allowed_materials": ["woods"],
            "base_power": 18,
            "damage_spread": 0.15,
            "base_durability": 35,
            "narrative_tags": ["bow", "long_range", "sniper"],
            "implicit_bonuses": {
                "physical_damage_bonus": 0.15,
                "physical_accuracy": 0.10,
            },
        },
        "crossbow": {
            "id": "crossbow",
            "name_ru": "Арбалет",
            "slot": "two_hand",
            "damage_type": "physical",
            "defense_type": None,
            "allowed_materials": ["woods", "ingots"],
            "base_power": 25,
            "damage_spread": 0.05,
            "base_durability": 60,
            "narrative_tags": ["crossbow", "heavy", "slow"],
            "implicit_bonuses": {
                "physical_penetration": 0.50,
                "physical_crit_power_float": 1.0,
            },
        },
    },
    # ==========================================
    # 5. ЩИТЫ (Off Hand Only)
    # ==========================================
    "shields": {
        "shield": {
            "id": "shield",
            "name_ru": "Щит",
            "slot": "off_hand",
            "damage_type": None,
            "defense_type": "physical",
            "allowed_materials": ["woods", "ingots"],
            "base_power": 15,
            "base_durability": 80,
            "damage_spread": 0.0,
            "narrative_tags": ["shield", "block", "protection"],
            "implicit_bonuses": {
                "shield_block_chance": 0.20,
                "shield_block_power": 0.30,
            },
        },
        "buckler": {
            "id": "buckler",
            "name_ru": "Баклер",
            "slot": "off_hand",
            "damage_type": None,
            "defense_type": "physical",
            "allowed_materials": ["woods", "ingots"],
            "base_power": 5,
            "base_durability": 50,
            "damage_spread": 0.0,
            "narrative_tags": ["buckler", "parry", "small_shield"],
            "implicit_bonuses": {
                "parry_chance": 0.15,
                "shield_block_chance": 0.05,
            },
        },
    },
}
