"""
Модуль содержит конфигурацию для различных сервисных хабов в игре.

Определяет, какие UI-билдеры и FSM-состояния должны быть активированы
при входе в конкретный хаб (например, Арену).
"""

from typing import Any, TypedDict

from apps.bot.resources.fsm_states import InGame
from apps.bot.ui_service.arena_ui_service.arena_ui_service import ArenaUIService
from apps.bot.ui_service.helpers_ui.stub_service import StubUIService


class HubConfig(TypedDict):
    """Словарь конфигурации для Сервисного Хаба."""

    title: str
    intro_text: str
    fsm_state: Any
    ui_builder_class: type[Any]
    render_method_name: str
    required_dependencies: list[str]  # <-- Новое поле


HUB_CONFIGS: dict[str, HubConfig] = {
    "svc_arena_main": {
        "title": "Ангар Арены",
        "intro_text": "Добро пожаловать в Ангар Арены. Здесь вы можете подать заявку на бой.",
        "fsm_state": InGame.arena,
        "ui_builder_class": ArenaUIService,
        "render_method_name": "view_main_menu",
        "required_dependencies": ["char_id", "actor_name"],
    },
    "svc_town_hall_hub": {
        "title": "Ратуша",
        "intro_text": "",
        "fsm_state": InGame.exploration,  # ИСПРАВЛЕНО: InGame.exploration
        "ui_builder_class": StubUIService,
        "render_method_name": "render_stub",
        "required_dependencies": ["title", "char_id"],
    },
    "svc_blacksmith_repair": {
        "title": "Кузница",
        "intro_text": "",
        "fsm_state": InGame.exploration,  # ИСПРАВЛЕНО: InGame.exploration
        "ui_builder_class": StubUIService,
        "render_method_name": "render_stub",
        "required_dependencies": ["title", "char_id"],
    },
    "svc_market_hub": {
        "title": "Рынок",
        "intro_text": "",
        "fsm_state": InGame.exploration,  # ИСПРАВЛЕНО: InGame.exploration
        "ui_builder_class": StubUIService,
        "render_method_name": "render_stub",
        "required_dependencies": ["title", "char_id"],
    },
    "svc_portal_hub": {
        "title": "Портал",
        "intro_text": "",
        "fsm_state": InGame.exploration,  # ИСПРАВЛЕНО: InGame.exploration
        "ui_builder_class": StubUIService,
        "render_method_name": "render_stub",
        "required_dependencies": ["title", "char_id"],
    },
    "svc_tavern_hub": {
        "title": "Таверна",
        "intro_text": "",
        "fsm_state": InGame.exploration,  # ИСПРАВЛЕНО: InGame.exploration
        "ui_builder_class": StubUIService,
        "render_method_name": "render_stub",
        "required_dependencies": ["title", "char_id"],
    },
}
