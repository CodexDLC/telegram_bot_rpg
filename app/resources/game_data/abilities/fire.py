"""
Модуль содержит определения способностей, связанных со стихией огня.

Каждая способность описывается структурой `AbilityData`, включающей
название, описание, стоимость ресурсов, правила применения и пайплайн
эффектов.
"""

from app.resources.game_data.ability_data_struct import AbilityData

FIRE_ABILITIES: dict[str, AbilityData] = {
    "fireball": {
        "name": "Огненный шар",
        "description": "Сгусток пламени, наносящий урон огнем.",
        "cost_energy": 30,
        "cost_tactics": 0,
        "cost_hp": 0,
        "rules": {
            "ignore_parry": True,
            "override_damage_type": "fire",
        },
        "pipeline": [
            {
                "phase": "post_calc",
                "trigger": "on_hit",
                "action": "apply_status",
                "target": "enemy",
                "params": {"status_id": "burn", "duration": 3, "power": 5},
            }
        ],
    },
}
