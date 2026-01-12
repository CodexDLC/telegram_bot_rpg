from apps.game_core.resources.game_data.feints.schemas import FeintDTO

# ==========================================
# ГЛОБАЛЬНЫЕ РЕЕСТРЫ (In-Memory DB)
# ==========================================

FEINT_REGISTRY: dict[str, FeintDTO] = {}


def _initialize_library() -> None:
    # TODO: Load definitions here
    pass


# ==========================================
# PUBLIC API
# ==========================================


def get_feint_config(feint_id: str) -> FeintDTO | None:
    return FEINT_REGISTRY.get(feint_id)


def get_all_feints() -> list[FeintDTO]:
    return list(FEINT_REGISTRY.values())


# Auto-init
_initialize_library()
