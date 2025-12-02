"""
Модуль содержит определения способностей, связанных с ядом.

Каждая способность описывается структурой `AbilityData`, включающей
название, описание, стоимость ресурсов, правила применения и пайплайн
эффектов.
"""

from app.resources.game_data.ability_data_struct import AbilityData

POISON_ABILITIES: dict[str, AbilityData] = {
    "poison_coat": {
        "name": "Ядовитая смазка",
        "description": "Покрывает оружие ядом на следующий удар.",
        "cost_energy": 15,
        "cost_tactics": 0,
        "cost_hp": 0,
        "rules": {},
        "pipeline": [
            {
                "phase": "post_calc",
                "trigger": "on_hit",
                "action": "apply_status",
                "target": "enemy",
                "params": {"status_id": "poison", "duration": 5, "power": 3},
            }
        ],
    }
}
