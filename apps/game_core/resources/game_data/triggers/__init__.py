from apps.game_core.resources.game_data.triggers.schemas import TriggerDTO

# ==========================================
# ГЛОБАЛЬНЫЕ РЕЕСТРЫ (In-Memory DB)
# ==========================================

TRIGGER_REGISTRY: dict[str, TriggerDTO] = {}


def _initialize_library() -> None:
    # TODO: Load definitions here
    pass


# ==========================================
# PUBLIC API
# ==========================================


def get_weapon_trigger(weapon_class: str) -> TriggerDTO | None:
    for trigger in TRIGGER_REGISTRY.values():
        if trigger.weapon_class == weapon_class:
            return trigger
    return None


def get_all_triggers() -> list[TriggerDTO]:
    return list(TRIGGER_REGISTRY.values())


# Auto-init
_initialize_library()
