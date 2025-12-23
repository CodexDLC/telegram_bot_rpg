from apps.game_core.resources.game_data.monsters.monster_structs import MonsterLoadout, MonsterStats, MonsterVariant

# Пул тренировочных монстров для туториала.
# БАЛАНС:
# - Гуманоиды: Средние статы, сила в экипировке.
# - Звери: Высокие статы, компенсирующие отсутствие вещей.

TRAINING_POOL: dict[str, MonsterVariant] = {
    # ==================================================
    # ГУМАНОИДЫ (Статы ниже, но есть броня и оружие)
    # ==================================================
    "goblin_spearman_training": {
        "id": "goblin_spearman_training",
        "role": "veteran",
        "narrative_hint": "A disciplined goblin with a long spear and a crude wooden shield.",
        "cost": 50,
        "extra_tags": ["infantry", "shield", "training"],
        "base_stats": MonsterStats(
            strength=10,
            agility=10,
            endurance=11,
            intelligence=5,
            wisdom=5,
            men=6,
            perception=9,
            charisma=5,
            luck=5,
        ),
        # Экипировка дает доп. защиту и урон
        "fixed_loadout": MonsterLoadout(main_hand="spear", off_hand="shield", chest_armor="jerkin"),
        "skills": ["attack_pierce", "buff_defense"],
    },
    "bandit_cutthroat_training": {
        "id": "bandit_cutthroat_training",
        "role": "veteran",
        "narrative_hint": "A quick and ruthless fighter with two daggers.",
        "cost": 50,
        "extra_tags": ["human", "outlaw", "training"],
        "base_stats": MonsterStats(
            strength=9,
            agility=16,  # Высокая ловкость для уклонения (легкая броня)
            endurance=8,
            intelligence=6,
            wisdom=4,
            men=8,
            perception=10,
            charisma=3,
            luck=12,
        ),
        "fixed_loadout": MonsterLoadout(
            main_hand="dagger",
            off_hand="dagger",
            chest_armor="jerkin",
            gloves_garment="work_gloves",
            belt_accessory="belt",
        ),
        "skills": ["poison_stab", "evasion"],
    },
    "goblin_slinger_training": {
        "id": "goblin_slinger_training",
        "role": "veteran",
        "narrative_hint": "A fast goblin with a sling. Keeps distance.",
        "cost": 50,
        "extra_tags": ["ranged", "fast", "training"],
        "base_stats": MonsterStats(
            strength=6,
            agility=15,  # Подняли ловкость, так как броня легкая
            endurance=10,
            intelligence=6,
            wisdom=7,
            men=5,
            perception=12,
            charisma=4,
            luck=7,
        ),
        # Исправлено: Добавлена праща и простая одежда
        "fixed_loadout": MonsterLoadout(main_hand="sling", chest_garment="shirt", legs_garment="trousers"),
        "skills": ["attack_ranged"],
    },
    # ==================================================
    # ЗВЕРИ (Статы ВЫШЕ, так как нет вещей)
    # ==================================================
    "wolf_stalker_training": {
        "id": "wolf_stalker_training",
        "role": "veteran",
        "narrative_hint": "A wolf that moves low to the ground. Stronger than an armed goblin naturally.",
        "cost": 50,
        "extra_tags": ["stealth", "hunter", "training"],
        "base_stats": MonsterStats(
            strength=14,  # +4 к силе по сравнению с гоблином (компенсация оружия)
            agility=14,  # Высокая ловкость
            endurance=15,  # +4 к выносливости (природная шкура вместо брони)
            intelligence=5,
            wisdom=4,
            men=7,
            perception=14,
            charisma=3,
            luck=5,
        ),
        "fixed_loadout": MonsterLoadout(),
        "skills": ["attack_heavy"],
    },
    "wolf_flanker_training": {
        "id": "wolf_flanker_training",
        "role": "veteran",
        "narrative_hint": "A clever wolf that attacks from behind.",
        "cost": 50,
        "extra_tags": ["tactical", "fast", "training"],
        "base_stats": MonsterStats(
            strength=13,
            agility=16,  # Очень быстрый
            endurance=14,
            intelligence=6,
            wisdom=4,
            men=8,
            perception=12,
            charisma=4,
            luck=5,
        ),
        "fixed_loadout": MonsterLoadout(),
        "skills": ["attack_fast", "debuff_weaken"],
    },
    "wolf_snapper_training": {
        "id": "wolf_snapper_training",
        "role": "veteran",
        "narrative_hint": "A wolf with powerful jaws. Hits very hard.",
        "cost": 50,
        "extra_tags": ["executioner", "strong_jaw", "training"],
        "base_stats": MonsterStats(
            strength=16,  # Очень сильный укус
            agility=12,
            endurance=16,  # Живучий
            intelligence=4,
            wisdom=3,
            men=8,
            perception=10,
            charisma=3,
            luck=5,
        ),
        "fixed_loadout": MonsterLoadout(),
        "skills": ["attack_execute", "debuff_stun"],
    },
}
