from typing import NamedTuple

from aiogram.fsm.state import State

from common.schemas.enums import CoreDomain
from game_client.bot.resources.fsm_states.states import BotState


# Config для режиссера: какой стейт включить и какой метод контейнера дернуть, чтобы получить Оркестратор
class SceneConfig(NamedTuple):
    fsm_state: State
    container_getter: str  # Имя метода в BotContainer (ex: "get_combat_bot_orchestrator")


# O(1) карта сцен
DIRECTOR_ROUTES: dict[str, SceneConfig] = {
    # --- Battle Scenes ---
    CoreDomain.COMBAT: SceneConfig(fsm_state=BotState.combat, container_getter="get_combat_bot_orchestrator"),
    # --- TODO: Migrate other domains ---
    # CoreDomain.EXPLORATION: SceneConfig(fsm_state=BotState.exploration, container_getter="get_exploration_bot_orchestrator"),
    # CoreDomain.SCENARIO: SceneConfig(fsm_state=BotState.scenario, container_getter="get_scenario_bot_orchestrator"),
    # CoreDomain.INVENTORY: SceneConfig(fsm_state=BotState.inventory, container_getter="get_inventory_bot_orchestrator"),
    # CoreDomain.LOBBY: SceneConfig(fsm_state=BotState.lobby, container_getter="get_lobby_bot_orchestrator"),
    # CoreDomain.STATUS: SceneConfig(fsm_state=BotState.status, container_getter="get_status_bot_orchestrator"),
    # CoreDomain.ONBOARDING: SceneConfig(fsm_state=BotState.onboarding, container_getter="get_onboarding_bot_orchestrator"),
    # CoreDomain.ARENA: SceneConfig(fsm_state=BotState.arena, container_getter="get_arena_bot_orchestrator"),
}
