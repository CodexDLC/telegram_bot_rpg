# apps/common/schemas_dto/auth_dto.py
from enum import StrEnum


class GameStage(StrEnum):
    """
    Глобальное состояние (этап) игры, в котором находится персонаж.
    Используется для восстановления сессии и блокировки неверных действий.
    """

    CREATION = "creation"
    TUTORIAL_STATS = "tutorial_stats"
    TUTORIAL_SKILL = "tutorial_skill"
    TUTORIAL_WORLD = "tutorial_world"
    IN_GAME = "in_game"

    # Состояния для Exploration Loop
    EXPLORATION_PENDING = "exploration_pending"  # Ожидание реакции на энкаунтер
    COMBAT = "combats"  # Активный бой
