"""
Модуль содержит конфигурацию для различных сервисных хабов в игре.

Определяет, какие UI-билдеры и FSM-состояния должны быть активированы
при входе в конкретный хаб (например, Арену).
"""

from typing import Any, TypedDict

from apps.bot.resources.fsm_states import ArenaState
from apps.bot.ui_service.arena_ui_service.arena_ui_service import ArenaUIService


class HubConfig(TypedDict):
    """Словарь конфигурации для Сервисного Хаба."""

    title: str
    intro_text: str
    fsm_state: Any
    ui_builder_class: type[Any]
    render_method_name: str


HUB_CONFIGS: dict[str, HubConfig] = {
    "svc_arena_main": {
        "title": "Ангар Арены",
        "intro_text": "Добро пожаловать в Ангар Арены. Здесь вы можете подать заявку на бой.",
        "fsm_state": ArenaState.menu,
        "ui_builder_class": ArenaUIService,
        "render_method_name": "view_main_menu",
    }
}
