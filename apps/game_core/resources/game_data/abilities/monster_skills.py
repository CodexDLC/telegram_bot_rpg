"""
Модуль содержит определения способностей монстров.

Каждая способность описывается структурой `AbilityData`, включающей
название, описание, стоимость ресурсов, правила применения и пайплайн
эффектов.
"""

from apps.game_core.resources.game_data.ability_data_struct import AbilityData

MONSTER_ABILITIES: dict[str, AbilityData] = {
    # --- АТАКИ ---
    "attack_pierce": {
        "name": "Пронзающий удар",
        "description": "Удар, игнорирующий часть брони.",
        "cost_energy": 15,
        "cost_tactics": 0,
        "cost_hp": 0,
        "rules": {
            "damage_mult": 1.1,
        },
        "pipeline": [
            {
                "phase": "pre_calc",
                "trigger": "always",
                "target": "self",
                "action": "modify_stat",
                "params": {"stat": "physical_penetration", "value": 0.2, "mode": "add"},
            }
        ],
    },
    "attack_heavy": {
        "name": "Тяжелый удар",
        "description": "Медленный, но мощный удар.",
        "cost_energy": 20,
        "cost_tactics": 0,
        "cost_hp": 0,
        "rules": {
            "damage_mult": 1.3,
        },
        "pipeline": [],
    },
    "attack_fast": {
        "name": "Быстрый укус",
        "description": "Молниеносная атака.",
        "cost_energy": 10,
        "cost_tactics": 0,
        "cost_hp": 0,
        "rules": {
            "damage_mult": 0.9,
        },
        "pipeline": [
            {
                "phase": "pre_calc",
                "trigger": "always",
                "target": "self",
                "action": "modify_stat",
                "params": {"stat": "physical_accuracy", "value": 0.2, "mode": "add"},
            }
        ],
    },
    "attack_execute": {
        "name": "Казнь",
        "description": "Добивающий удар.",
        "cost_energy": 30,
        "cost_tactics": 0,
        "cost_hp": 0,
        "rules": {
            "damage_mult": 1.5,
        },
        "pipeline": [],
    },
    "attack_ranged": {
        "name": "Выстрел",
        "description": "Атака с дистанции.",
        "cost_energy": 10,
        "cost_tactics": 0,
        "cost_hp": 0,
        "rules": {},
        "pipeline": [],
    },
    "poison_stab": {
        "name": "Отравленный укол",
        "description": "Удар, накладывающий яд.",
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
                "params": {"status_id": "poison", "duration": 3, "power": 2},
            }
        ],
    },
    # --- БАФФЫ / ДЕБАФФЫ ---
    "buff_defense": {
        "name": "Защитная стойка",
        "description": "Повышает защиту.",
        "cost_energy": 15,
        "cost_tactics": 0,
        "cost_hp": 0,
        "rules": {},
        "pipeline": [
            {
                "phase": "post_calc",
                "trigger": "always",
                "action": "apply_status",
                "target": "self",
                "params": {"status_id": "defense_up", "duration": 2, "power": 0.2},
            }
        ],
    },
    "evasion": {
        "name": "Уклонение",
        "description": "Повышает шанс уклонения.",
        "cost_energy": 15,
        "cost_tactics": 0,
        "cost_hp": 0,
        "rules": {},
        "pipeline": [
            {
                "phase": "post_calc",
                "trigger": "always",
                "action": "apply_status",
                "target": "self",
                "params": {"status_id": "evasion_up", "duration": 2, "power": 0.2},
            }
        ],
    },
    "debuff_weaken": {
        "name": "Ослабление",
        "description": "Снижает урон противника.",
        "cost_energy": 20,
        "cost_tactics": 0,
        "cost_hp": 0,
        "rules": {},
        "pipeline": [
            {
                "phase": "post_calc",
                "trigger": "on_hit",
                "action": "apply_status",
                "target": "enemy",
                "params": {"status_id": "weaken", "duration": 3, "power": 0.15},
            }
        ],
    },
    "debuff_stun": {
        "name": "Оглушение",
        "description": "Оглушает противника.",
        "cost_energy": 40,
        "cost_tactics": 0,
        "cost_hp": 0,
        "rules": {},
        "pipeline": [
            {
                "phase": "post_calc",
                "trigger": "on_hit",
                "action": "apply_status",
                "target": "enemy",
                "params": {"status_id": "stun", "duration": 1, "power": 1},
            }
        ],
    },
}
