from typing import NamedTuple

from aiogram.fsm.state import State

from src.frontend.bot.resources.fsm_states.states import BotState
from src.shared.enums.domain_enums import CoreDomain


# Config для режиссера: какой стейт включить и какой сервис вызвать при входе
class SceneConfig(NamedTuple):
    fsm_state: State
    entry_service: str  # Ключ в RENDER_ROUTES[feature] для entry point


# =============================================================================
# SCENE_ROUTES: Межфичевые переходы (смена FSM State)
# =============================================================================
SCENE_ROUTES: dict[str, SceneConfig] = {
    CoreDomain.COMBAT: SceneConfig(fsm_state=BotState.combat, entry_service="hud"),
    CoreDomain.EXPLORATION: SceneConfig(fsm_state=BotState.exploration, entry_service="navigation"),
    CoreDomain.SCENARIO: SceneConfig(fsm_state=BotState.scenario, entry_service="main"),
    CoreDomain.INVENTORY: SceneConfig(fsm_state=BotState.inventory, entry_service="main"),
    CoreDomain.LOBBY: SceneConfig(fsm_state=BotState.lobby, entry_service="main"),
    CoreDomain.STATUS: SceneConfig(fsm_state=BotState.status, entry_service="main"),
    CoreDomain.ONBOARDING: SceneConfig(fsm_state=BotState.onboarding, entry_service="main"),
    CoreDomain.ARENA: SceneConfig(fsm_state=BotState.arena, entry_service="main"),
}

# Alias для обратной совместимости
DIRECTOR_ROUTES = SCENE_ROUTES


# =============================================================================
# RENDER_ROUTES: Внутрифичевые переходы (без смены FSM State)
# feature -> service -> container_getter
# =============================================================================
RENDER_ROUTES: dict[str, dict[str, str]] = {
    CoreDomain.COMBAT: {
        "hud": "get_combat_bot_orchestrator",
    },
    CoreDomain.EXPLORATION: {
        "navigation": "get_navigation_orchestrator",
        "interaction": "get_interaction_orchestrator",
    },
    CoreDomain.SCENARIO: {
        "main": "get_scenario_bot_orchestrator",
    },
    CoreDomain.INVENTORY: {
        "main": "get_inventory_bot_orchestrator",
    },
    CoreDomain.LOBBY: {
        "main": "get_lobby_bot_orchestrator",
    },
    CoreDomain.STATUS: {
        "main": "get_status_bot_orchestrator",
    },
    CoreDomain.ONBOARDING: {
        "main": "get_onboarding_bot_orchestrator",
    },
    CoreDomain.ARENA: {
        "main": "get_arena_bot_orchestrator",
    },
}
