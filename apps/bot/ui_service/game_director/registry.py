# apps/bot/ui_service/game_director/registry.py
from typing import NamedTuple

from aiogram.fsm.state import State

from apps.bot.resources.fsm_states.states import BotState
from apps.common.schemas_dto.game_state_enum import GameState


# Config для режиссера: какой стейт включить и какой метод контейнера дернуть, чтобы получить Оркестратор
class SceneConfig(NamedTuple):
    fsm_state: State
    container_getter: str  # Имя метода в AppContainer (ex: "get_combat_bot_orchestrator")


# O(1) карта сцен
DIRECTOR_ROUTES: dict[str, SceneConfig] = {
    # --- Battle Scenes ---
    GameState.COMBAT: SceneConfig(fsm_state=BotState.combat, container_getter="get_combat_bot_orchestrator"),
    # --- World Scenes ---
    GameState.EXPLORATION: SceneConfig(
        fsm_state=BotState.exploration, container_getter="get_exploration_bot_orchestrator"
    ),
    GameState.SCENARIO: SceneConfig(fsm_state=BotState.scenario, container_getter="get_scenario_bot_orchestrator"),
    # --- Menu Scenes ---
    GameState.INVENTORY: SceneConfig(fsm_state=BotState.inventory, container_getter="get_inventory_bot_orchestrator"),
    GameState.LOBBY: SceneConfig(
        fsm_state=BotState.lobby,  # FIXED: Используем BotState.lobby
        container_getter="get_lobby_bot_orchestrator",
    ),
    GameState.STATUS: SceneConfig(fsm_state=BotState.status, container_getter="get_status_bot_orchestrator"),
    GameState.ONBOARDING: SceneConfig(
        fsm_state=BotState.onboarding, container_getter="get_onboarding_bot_orchestrator"
    ),
    GameState.ARENA: SceneConfig(fsm_state=BotState.arena, container_getter="get_arena_bot_orchestrator"),
}
