from apps.game_core.resources.game_data.abilities.schemas import AbilityDTO

# ==========================================
# ГЛОБАЛЬНЫЕ РЕЕСТРЫ (In-Memory DB)
# ==========================================

ABILITY_REGISTRY: dict[str, AbilityDTO] = {}


def _initialize_library() -> None:
    # TODO: Load definitions here
    pass


# ==========================================
# PUBLIC API
# ==========================================


def get_ability_config(ability_id: str) -> AbilityDTO | None:
    return ABILITY_REGISTRY.get(ability_id)


def get_all_abilities() -> list[AbilityDTO]:
    return list(ABILITY_REGISTRY.values())


# Auto-init
_initialize_library()
