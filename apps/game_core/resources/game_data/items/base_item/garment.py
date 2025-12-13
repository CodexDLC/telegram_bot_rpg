"""
РУКОВОДСТВО ПО ЗАПОЛНЕНИЮ: ОДЕЖДА (GARMENT)
===========================================

Этот файл содержит шаблоны для одежды, которая надевается в слоты "внешнего вида".
Она не дает существенной физической защиты, но защищает от агрессивной среды (разломов).

КЛЮЧЕВЫЕ ПОЛЯ:
---------------
- slot: 'chest_garment', 'legs_garment', 'outer_garment', 'gloves_garment'.
- implicit_bonuses: Используйте бонусы для защиты от среды:
    - 'environment_cold_resistance' (для ледяных разломов)
    - 'environment_heat_resistance' (для огненных разломов)
    - 'environment_gravity_resistance' (для гравитационных аномалий)
    - 'environment_bio_resistance' (для био-разломов)
"""

GARMENT_DB = {
    "garment": {
        # ==========================================
        # ЛЕГКАЯ ОДЕЖДА (Защита от Жары / Огня)
        # ==========================================
        "linen_shirt": {
            "id": "linen_shirt",
            "name_ru": "Льняная рубаха",
            "slot": "chest_garment",
            "damage_type": None,
            "defense_type": None,
            "allowed_materials": ["cloths"],
            "base_power": 0,
            "base_durability": 20,
            "damage_spread": 0.0,
            "narrative_tags": ["shirt", "light", "breathable"],
            "implicit_bonuses": {"environment_heat_resistance": 5.0},
        },
        "linen_pants": {
            "id": "linen_pants",
            "name_ru": "Льняные штаны",
            "slot": "legs_garment",
            "damage_type": None,
            "defense_type": None,
            "allowed_materials": ["cloths"],
            "base_power": 0,
            "base_durability": 20,
            "damage_spread": 0.0,
            "narrative_tags": ["pants", "light", "loose"],
            "implicit_bonuses": {"environment_heat_resistance": 5.0},
        },
        "desert_wrap": {
            "id": "desert_wrap",
            "name_ru": "Пустынная накидка",
            "slot": "outer_garment",
            "damage_type": None,
            "defense_type": None,
            "allowed_materials": ["cloths"],
            "base_power": 1,
            "base_durability": 25,
            "damage_spread": 0.0,
            "narrative_tags": ["wrap", "dust_protection", "nomad"],
            "implicit_bonuses": {
                "environment_heat_resistance": 8.0,
                "environment_gravity_resistance": 2.0,  # Защита от пыли/ветра
            },
        },
        # ==========================================
        # ТЕПЛАЯ ОДЕЖДА (Защита от Холода / Льда)
        # ==========================================
        "wool_tunic": {
            "id": "wool_tunic",
            "name_ru": "Шерстяная туника",
            "slot": "chest_garment",
            "damage_type": None,
            "defense_type": None,
            "allowed_materials": ["cloths", "leathers"],
            "base_power": 1,
            "base_durability": 30,
            "damage_spread": 0.0,
            "narrative_tags": ["tunic", "warm", "thick"],
            "implicit_bonuses": {"environment_cold_resistance": 5.0},
        },
        "fur_pants": {
            "id": "fur_pants",
            "name_ru": "Меховые штаны",
            "slot": "legs_garment",
            "damage_type": None,
            "defense_type": None,
            "allowed_materials": ["leathers"],
            "base_power": 1,
            "base_durability": 30,
            "damage_spread": 0.0,
            "narrative_tags": ["pants", "fur", "warm"],
            "implicit_bonuses": {"environment_cold_resistance": 5.0},
        },
        "winter_cloak": {
            "id": "winter_cloak",
            "name_ru": "Зимний плащ",
            "slot": "outer_garment",
            "damage_type": None,
            "defense_type": None,
            "allowed_materials": ["leathers", "cloths"],
            "base_power": 2,
            "base_durability": 40,
            "damage_spread": 0.0,
            "narrative_tags": ["cloak", "fur_lined", "heavy"],
            "implicit_bonuses": {"environment_cold_resistance": 10.0},
        },
        "mittens": {
            "id": "mittens",
            "name_ru": "Варежки",
            "slot": "gloves_garment",
            "damage_type": None,
            "defense_type": None,
            "allowed_materials": ["cloths", "leathers"],
            "base_power": 0,
            "base_durability": 20,
            "damage_spread": 0.0,
            "narrative_tags": ["mittens", "warm", "cozy"],
            "implicit_bonuses": {
                "environment_cold_resistance": 3.0,
                "crafting_speed": -0.05,  # Неудобно работать
            },
        },
        # ==========================================
        # РАБОЧАЯ ОДЕЖДА (Защита от Био / Грязи)
        # ==========================================
        "apron": {
            "id": "apron",
            "name_ru": "Плотный фартук",
            "slot": "chest_garment",
            "damage_type": None,
            "defense_type": None,
            "allowed_materials": ["leathers", "cloths"],
            "base_power": 1,
            "base_durability": 35,
            "damage_spread": 0.0,
            "narrative_tags": ["apron", "protective", "thick"],
            "implicit_bonuses": {
                "environment_bio_resistance": 5.0,
                "crafting_speed": 0.05,
            },
        },
        "work_gloves": {
            "id": "work_gloves",
            "name_ru": "Рабочие перчатки",
            "slot": "gloves_garment",
            "damage_type": None,
            "defense_type": None,
            "allowed_materials": ["leathers"],
            "base_power": 0,
            "base_durability": 40,
            "damage_spread": 0.0,
            "narrative_tags": ["gloves", "durable", "rough"],
            "implicit_bonuses": {
                "environment_bio_resistance": 2.0,
                "crafting_speed": 0.10,  # Удобно для крафта
            },
        },
    },
}
