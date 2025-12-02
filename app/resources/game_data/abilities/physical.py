"""
Модуль содержит определения физических способностей.

Каждая способность описывается структурой `AbilityData`, включающей
название, описание, стоимость ресурсов, правила применения и пайплайн
эффектов.
"""

from app.resources.game_data.ability_data_struct import AbilityData

PHYSICAL_ABILITIES: dict[str, AbilityData] = {
    "shadow_strike": {
        "name": "Удар из Тени",
        "description": "Коварный удар, игнорирующий щиты.",
        "cost_energy": 20,
        "cost_tactics": 1,
        "cost_hp": 0,
        "rules": {
            "ignore_block": True,
            "damage_mult": 1.2,
        },
        "pipeline": [],
    },
}
