from apps.game_core.resources.game_data.abilities.schemas import (
    AbilityConfigDTO,
    AbilityCostDTO,
)

DEBUG_ABILITIES = [
    AbilityConfigDTO(
        ability_id="debug_fireball",
        name_ru="Тестовый Фаербол",
        description_ru="Debug ability for testing registry loading.",
        cost=AbilityCostDTO(energy=10, gift=1),
        pipeline_mutations={
            "damage.fire": True,
        },
        post_calc_effects=[
            {
                "effect_id": "debug_burn",
                "duration": 3,
                "params": {"power": 1},
            }
        ],
    ),
]
