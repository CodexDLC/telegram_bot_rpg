from apps.game_core.resources.game_data.effects.schemas import EffectDTO

# ==========================================
# ГЛОБАЛЬНЫЕ РЕЕСТРЫ (In-Memory DB)
# ==========================================

EFFECT_REGISTRY: dict[str, EffectDTO] = {}


def _initialize_library() -> None:
    # TODO: Load definitions here
    pass


# ==========================================
# PUBLIC API
# ==========================================


def get_effect_config(effect_id: str) -> EffectDTO | None:
    return EFFECT_REGISTRY.get(effect_id)


def get_all_effects() -> list[EffectDTO]:
    return list(EFFECT_REGISTRY.values())


# Auto-init
_initialize_library()
