# app/resources/game_data/hub_config.py
from typing import Any, TypedDict

from app.resources.fsm_states.states import ArenaState
from app.services.ui_service.arena_ui_service.arena_builder import ArenaUIBuilder


# --- Типизация для словаря (для чистоты) ---
class HubConfig(TypedDict):
    """Словарь конфигурации для Сервисного Хаба."""

    title: str
    intro_text: str
    fsm_state: Any  # FSM-состояние, в которое перейдет игрок (например, InGame.arena_menu)
    ui_builder_class: type[Any]  # Ссылка на класс-билдер UI (например, ArenaMenuBuilder)
    render_method_name: str


# --- ГЛАВНЫЙ СЛОВАРЬ КОНФИГУРАЦИИ ---
# Ключом является target_loc из ServiceEntryCallback (например, 'svc_arena_main')
HUB_CONFIGS: dict[str, HubConfig] = {
    "svc_arena_main": {
        "title": "Ангар Арены",
        "intro_text": "Добро пожаловать в Ангар Арены. Здесь вы можете подать заявку на бой.",
        "fsm_state": ArenaState.menu,
        "ui_builder_class": ArenaUIBuilder,
        "render_method_name": "render_menu",
    }
}
