from collections import defaultdict
from typing import Any

from loguru import logger as log

from apps.game_core.resources.game_data.triggers.definitions.weapon_triggers import WEAPON_TRIGGERS
from apps.game_core.resources.game_data.triggers.schemas import TriggerDTO

# ==========================================
# 1. ГЛОБАЛЬНЫЙ РЕЕСТР (UI / META)
# ==========================================
# Используется для отображения информации о триггерах (иконки, описание).
TRIGGER_REGISTRY: dict[str, TriggerDTO] = {}

# ==========================================
# 2. ПРАВИЛА БОЯ (LOGIC / RESOLVER)
# ==========================================
# Оптимизированный индекс для CombatResolver.
# Структура: { "ON_CRIT": { "trigger_id": { "chance": 1.0, "mutations": {...} } } }
TRIGGER_RULES: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)


def _register_triggers(trigger_list: list[TriggerDTO]) -> None:
    for trigger in trigger_list:
        # 1. Registry (UI)
        if trigger.id in TRIGGER_REGISTRY:
            log.warning(f"TriggerLibrary | Duplicate trigger ID: '{trigger.id}'. Overwriting.")
        TRIGGER_REGISTRY[trigger.id] = trigger

        # 2. Rules (Logic)
        # Преобразуем DTO в формат правил для резолвера
        TRIGGER_RULES[trigger.event][trigger.id] = {
            "chance": trigger.chance,
            "mutations": trigger.mutations,
        }


def _initialize_library() -> None:
    log.info("TriggerLibrary | Initializing...")

    # Здесь будут добавляться списки из других файлов (ability_triggers, etc.)
    all_groups = [WEAPON_TRIGGERS]
    count = 0

    for group in all_groups:
        _register_triggers(group)
        count += len(group)

    log.info(f"TriggerLibrary | Loaded {count} triggers. Rules compiled for {len(TRIGGER_RULES)} events.")


# ==========================================
# PUBLIC API
# ==========================================


def get_trigger_config(trigger_id: str) -> TriggerDTO | None:
    """Получить полное описание триггера (для UI)."""
    return TRIGGER_REGISTRY.get(trigger_id)


def get_all_triggers() -> list[TriggerDTO]:
    return list(TRIGGER_REGISTRY.values())


def get_weapon_trigger(weapon_class: str) -> TriggerDTO | None:
    """
    DEPRECATED: Триггеры теперь не привязаны жестко к классу оружия в коде.
    Связь идет через поле triggers в BaseItemDTO.
    """
    log.warning("Using deprecated function get_weapon_trigger. Use item.triggers list instead.")
    return None


# Auto-init
_initialize_library()
