"""
Модуль содержит DTO (Data Transfer Objects) для боевой системы (RBC v3.0).
Охватывает ВНЕШНИЕ контракты: API, UI, Ingress.
Внутренние DTO перенесены в apps/game_core/modules/combat/dto/combat_internal_dto.py
"""

from typing import Any, NamedTuple, TypedDict

from pydantic import BaseModel

# ==============================================================================
# 1. 📦 PAYLOADS (TypedDicts for Polymorphism)
# ==============================================================================


class ItemPayload(TypedDict):
    """Данные для стратегии 'item'."""

    item_id: int
    target_id: int | str  # ID цели или инструкция ("self", "all_enemies")


class InstantPayload(TypedDict):
    """Данные для стратегии 'instant' (Skills)."""

    skill_id: str
    target_id: int | str


class ExchangePayload(TypedDict):
    """Данные для стратегии 'exchange' (Combat)."""

    target_id: int  # Конкретный ID оппонента
    attack_zones: list[str]  # ["head"]
    block_zones: list[str]  # ["body", "legs"]

    # Опционально (чем бьем)
    skill_id: str | None
    item_id: int | None  # Если это граната/метательное в бою


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
    tokens: dict[str, int]  # {"tactics": 5, "gift": 1}

    # Строка 3 (Status)
    effects: list[str]  # ["burn", "stun"] (ID иконок)


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

    logs: list[CombatLogEntryDTO] = []


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
