from loguru import logger as log

from apps.game_core.resources.game_data.abilities.definitions.debug import DEBUG_ABILITIES
from apps.game_core.resources.game_data.abilities.schemas import AbilityConfigDTO

# ==========================================
# ГЛОБАЛЬНЫЕ РЕЕСТРЫ (In-Memory DB)
# ==========================================

ABILITY_REGISTRY: dict[str, AbilityConfigDTO] = {}


def _register_abilities(ability_list: list[AbilityConfigDTO]) -> None:
    for ability in ability_list:
        if ability.ability_id in ABILITY_REGISTRY:
            log.warning(f"AbilityLibrary | Duplicate ability ID: '{ability.ability_id}'. Overwriting.")
        ABILITY_REGISTRY[ability.ability_id] = ability


def _initialize_library() -> None:
    log.info("AbilityLibrary | Initializing...")

    all_groups = [DEBUG_ABILITIES]
    count = 0

    for group in all_groups:
        _register_abilities(group)
        count += len(group)

    log.info(f"AbilityLibrary | Loaded {count} abilities.")


# ==========================================
# PUBLIC API
# ==========================================


def get_ability_config(ability_id: str) -> AbilityConfigDTO | None:
    return ABILITY_REGISTRY.get(ability_id)


def get_all_abilities() -> list[AbilityConfigDTO]:
    return list(ABILITY_REGISTRY.values())


# Auto-init
_initialize_library()
