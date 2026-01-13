from apps.game_core.resources.game_data.effects.schemas import EffectDTO, EffectType

DEBUG_EFFECTS = [
    EffectDTO(
        effect_id="debug_burn",
        name_en="Debug Burn",
        name_ru="Тестовое Горение",
        type=EffectType.DOT,
        duration=3,
        impact_flat={},
        scaling={"source": "snapshot_damage", "stat": "hp", "power": 1},
        modifiers={},
        flags={},
        description="Debug effect for testing registry loading.",
    ),
]
