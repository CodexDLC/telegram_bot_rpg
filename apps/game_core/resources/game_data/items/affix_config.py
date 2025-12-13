from typing import TypedDict

# --- 1. АТОМАРНЫЕ ЭФФЕКТЫ ---
# Это кирпичики. Значения указаны для Tier Multiplier = 1.0.
# При сборке: Final_Value = Base_Value * Material_Tier_Mult


class EffectData(TypedDict):
    target_field: str  # Поле в DTO (bonuses)
    base_value: float  # Значение (например 0.05 = 5%)
    is_percentage: bool  # Для форматирования в UI (+5% или +5 ед.)
    narrative_tags: list[str]


EFFECTS_DB: dict[str, EffectData] = {
    "phys_dmg_flat": {
        "target_field": "physical_damage_bonus",
        "base_value": 5.0,  # +5 урона на Тир 1
        "is_percentage": False,
        "narrative_tags": ["deadly", "impact"],
    },
    "crit_chance": {
        "target_field": "crit_chance",
        "base_value": 0.02,  # +2% крита на Тир 1
        "is_percentage": True,
        "narrative_tags": ["sharp", "precision"],
    },
    "dodge": {
        "target_field": "dodge_chance",
        "base_value": 0.02,
        "is_percentage": True,
        "narrative_tags": ["agile", "wind", "elusive"],
    },
    "lifesteal": {
        "target_field": "lifesteal_power",
        "base_value": 0.01,  # 1% вампиризма
        "is_percentage": True,
        "narrative_tags": ["blood", "parasitic"],
    },
    "hp_max": {
        "target_field": "hp_max_bonus",
        "base_value": 20.0,
        "is_percentage": False,
        "narrative_tags": ["vitality", "sturdy"],
    },
}


# --- 2. БАНДЛЫ (СУФФИКСЫ) ---
# Это сеты эффектов. Они требуют конкретного ресурса (Эссенции) для крафта.


class BundleData(TypedDict):
    id: str
    # Если это крафт - нужен ингредиент. Если лут - просто ID.
    ingredient_id: str  # Ссылка на RAW_RESOURCES_DB['essences']
    cost_slots: int  # Сколько слотов занимает в предмете
    min_tier: int  # Минимальный тир материала
    effects: list[str]  # Ключи из EFFECTS_DB
    narrative_tags: list[str]  # Теги для LLM ("Sword [of Vampire]")


BUNDLES_DB: dict[str, BundleData] = {
    # Бандл "Вампира" (делается из Флакона Крови)
    "vampire": {
        "id": "vampire",
        "ingredient_id": "essence_blood_vial",
        "cost_slots": 2,  # Занимает 2 слота (нужна сталь или выше)
        "min_tier": 2,  # Только на редких вещах
        "effects": ["lifesteal", "phys_dmg_flat"],
        "narrative_tags": ["vampire", "blood", "crimson", "thirsty"],
    },
    # Бандл "Тени" (делается из Пыли Теней)
    "shadow": {
        "id": "shadow",
        "ingredient_id": "essence_shadow_dust",
        "cost_slots": 1,  # Влезает даже в железо
        "min_tier": 1,
        "effects": ["dodge", "crit_chance"],
        "narrative_tags": ["shadow", "silent", "assassin", "hidden"],
    },
}
