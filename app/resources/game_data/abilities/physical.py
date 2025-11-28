# app/resources/game_data/abilities/physical.py
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
        "pipeline": [
            # Основной урон идет через базовую атаку с флагами rules.
            # Можно добавить эффект кровотечения при крите:
            # {
            #     "phase": "post_calc",
            #     "trigger": "on_crit",
            #     "action": "apply_status",
            #     "target": "enemy",
            #     "params": {"status_id": "bleed", "duration": 2, "power": 3}
            # }
        ],
    },
}
