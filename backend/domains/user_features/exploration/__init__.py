# backend/domains/user_features/exploration/__init__.py
"""
Exploration Domain - Исследование мира.

Отвечает за:
- Перемещение игрока по локациям
- Навигационный интерфейс (3x3 сетка)
- Случайные встречи (энкаунтеры)
- Вход в сервисы (таверна, арена и т.д.)
"""

from backend.domains.user_features.exploration.engine import EncounterEngine, NavigationEngine
from backend.domains.user_features.exploration.gateway import ExplorationGateway
from backend.domains.user_features.exploration.services import ExplorationService, ExplorationSessionService

__all__ = [
    # Gateway
    "ExplorationGateway",
    # Services
    "ExplorationService",
    "ExplorationSessionService",
    # Engines
    "EncounterEngine",
    "NavigationEngine",
]
