from apps.game_core.resources.game_data.triggers.schemas import TriggerDTO

WEAPON_TRIGGERS = [
    # --- SWORDS (Bleed on Crit) ---
    TriggerDTO(
        id="trigger_bleed",
        name_ru="Кровотечение",
        description_ru="Критические удары вызывают глубокое кровотечение вместо повышенного урона.",
        icon="bleed.png",
        event="ON_CRIT",
        chance=1.0,
        mutations={
            # Отключаем стандартный буст урона крита
            "crit_damage_boost": False,
            # Сообщаем AbilityService наложить эффект
            "apply_bleed": True,
            # Параметры эффекта (читаются в AbilityService)
            "pending_effect_data": {
                "bleed_strength": 0.3,  # 30% от урона
                "duration": 3,
            },
        },
    ),
    # --- POLEARMS / HAMMERS (Heavy Strike) ---
    TriggerDTO(
        id="trigger_heavy_strike",
        name_ru="Тяжёлый удар",
        description_ru="Критические удары наносят тройной урон.",
        icon="heavy_smash.png",
        event="ON_CRIT",
        chance=1.0,
        mutations={
            # Включаем буст урона
            "crit_damage_boost": True,
            # Устанавливаем множитель (вместо стандартного x1.5)
            "weapon_effect_value": 3.0,
        },
    ),
    # --- MACES (Stun on Crit) ---
    TriggerDTO(
        id="trigger_stun",
        name_ru="Оглушение",
        description_ru="Критические удары оглушают противника.",
        icon="stun.png",
        event="ON_CRIT",
        chance=1.0,
        mutations={
            "crit_damage_boost": True,  # Урон проходит
            "apply_stun": True,
            "pending_effect_data": {"duration": 1},
        },
    ),
    # --- BOWS (Evasion on Hit) ---
    TriggerDTO(
        id="trigger_evasive_shot",
        name_ru="Уклонение",
        description_ru="Попадание дает возможность гарантированно уклониться от следующей атаки.",
        icon="evasion.png",
        event="ON_HIT",
        chance=1.0,
        mutations={
            "grant_evasion_marker": True,
        },
    ),
]
