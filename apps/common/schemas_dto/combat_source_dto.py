"""
Модуль содержит DTO (Data Transfer Objects) для боевой системы (RBC v3.0).
Охватывает ВНЕШНИЕ контракты: API, UI, Ingress.
Внутренние DTO перенесены в apps/game_core/modules/combat/dto/combat_internal_dto.py
"""

from enum import Enum
from typing import Any, NamedTuple

from pydantic import BaseModel

# ==============================================================================
# 1. 📦 PAYLOADS (Polymorphic Intents)
# ==============================================================================


class TargetType(str, Enum):
    SELF = "self"
    SINGLE_ENEMY = "single_enemy"
    ALL_ENEMIES = "all_enemies"
    SINGLE_ALLY = "single_ally"
    ALL_ALLIES = "all_allies"
    RANDOM_ENEMY = "random_enemy"
    LOWEST_HP_ALLY = "lowest_hp_ally"
    LOWEST_HP_ENEMY = "lowest_hp_enemy"
    CLEAVE = "cleave"  # Атака по 3 целям


class ExchangePayload(BaseModel):
    """Данные для стратегии 'exchange' (Combat)."""

    target_id: int  # В обмене всегда одна конкретная цель (ID)

    # Финт (опционально)
    feint_id: str | None = None


class InstantPayload(BaseModel):
    """Данные для стратегии 'instant' (Abilities / Items)."""

    # В инстанте может быть ID, список ID или инструкция (TargetType)
    target_id: int | str | list[int] | None = None

    ability_id: str | None = None  # ID способности
    item_id: int | None = None  # ID предмета (если это расходник)
    feint_id: str | None = None  # ID финта (если это мгновенный финт, например "песок в глаза")


# ==============================================================================
# 2. 🖥️ UI / DASHBOARD (Client View)
# ==============================================================================


class CombatLogEntryDTO(BaseModel):
    """Одна запись лога."""

    text: str
    timestamp: float
    tags: list[str] = []


class ActorShortInfo(BaseModel):
    """Минимальная инфа для списков"""

    char_id: int
    name: str
    hp_percent: int
    is_dead: bool
    is_target: bool = False  # Выделение в списке


class ActorFullInfo(BaseModel):
    """Полная инфа для Hero и Target"""

    char_id: int
    name: str
    team: str

    # Строка 1
    hp_current: int
    hp_max: int
    energy_current: int
    energy_max: int

    # Для кнопок
    weapon_type: str  # "sword", "bow", "staff" (из main_hand)

    # Строка 2 (Tokens)
    # Суммарные токены (свободные + замороженные в руке)
    tokens: dict[str, int]  # {"tactics": 5, "gift": 1}

    # Строка 3 (Status)
    effects: list[str]  # ["burn", "stun"] (ID иконок)

    # Строка 4 (Feints Hand)
    feints: dict[str, str] = {}  # {"sand_throw": "Бросок песка"}


class CombatDashboardDTO(BaseModel):
    """Полный снимок экрана боя."""

    turn_number: int
    status: str  # active / waiting / finished

    # Блок 1: Я
    hero: ActorFullInfo

    # Блок 2: Цель (если есть)
    target: ActorFullInfo | None = None

    # Блок 3: Списки (для контекста)
    allies: list[ActorShortInfo]
    enemies: list[ActorShortInfo]

    winner_team: str | None = None

    # logs удалены, так как грузятся отдельно


class CombatLogDTO(BaseModel):
    """Логи с пагинацией."""

    logs: list[CombatLogEntryDTO]
    total: int
    page: int


# ==============================================================================
# 3. 🔄 DATA TRANSFER (Persistence)
# ==============================================================================


class SessionDataDTO(NamedTuple):
    """DTO for transferring assembled data to the persistence method."""

    meta: dict[str, Any]
    actors: dict[str, dict[str, Any]]  # final_id -> {key: value} (HASH/JSON fields)
    targets: dict[str, list[str]]  # final_id -> [enemy_id, ...]
