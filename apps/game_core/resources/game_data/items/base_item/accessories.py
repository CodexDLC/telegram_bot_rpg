"""
РУКОВОДСТВО ПО ЗАПОЛНЕНИЮ: АКСЕССУАРЫ
=====================================

Этот файл содержит шаблоны для бижутерии и поясов.

КЛЮЧЕВЫЕ ПОЛЯ:
---------------
- slot: 'ring_1', 'ring_2', 'amulet', 'earring', 'belt_accessory'.
- base_power: Обычно 0, так как основная сила в бонусах.
- implicit_bonuses:
    - Кольца/Амулеты: Могут давать любые бонусы к статам.
    - Пояса: 'quick_slot_capacity' определяет БАЗОВОЕ кол-во слотов (для тира 0).
"""

ACCESSORIES_DB = {
    "accessories": {
        "ring": {
            "id": "ring",
            "name_ru": "Кольцо",
            "slot": "ring_1",
            "damage_type": None,
            "defense_type": "magical",
            "allowed_materials": ["ingots"],
            "base_power": 0,
            "base_durability": 100,
            "damage_spread": 0.0,
            "narrative_tags": ["ring", "jewelry"],
            "implicit_bonuses": {},
        },
        "amulet": {
            "id": "amulet",
            "name_ru": "Амулет",
            "slot": "amulet",
            "damage_type": None,
            "defense_type": "magical",
            "allowed_materials": ["ingots", "essences"],
            "base_power": 0,
            "base_durability": 100,
            "damage_spread": 0.0,
            "narrative_tags": ["amulet", "necklace"],
            "implicit_bonuses": {"magical_resistance": 0.05},
        },
        "earring": {
            "id": "earring",
            "name_ru": "Серьга",
            "slot": "earring",
            "damage_type": None,
            "defense_type": "magical",
            "allowed_materials": ["ingots", "essences"],
            "base_power": 0,
            "base_durability": 100,
            "damage_spread": 0.0,
            "narrative_tags": ["earring", "jewelry"],
            "implicit_bonuses": {"control_resistance": 0.05},
        },
        # --- ЕДИНЫЙ БАЗОВЫЙ ПОЯС ---
        "belt": {
            "id": "belt",
            "name_ru": "Пояс",
            "slot": "belt_accessory",
            "damage_type": None,
            "defense_type": "physical",
            "allowed_materials": ["leathers", "cloths"],
            "base_power": 1,
            "base_durability": 40,
            "damage_spread": 0.0,
            "narrative_tags": ["belt", "waist"],
            "implicit_bonuses": {"quick_slot_capacity": 1.0},
        },
    },
}
