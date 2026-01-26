from typing import Any, TypedDict

from pydantic import BaseModel

from common.schemas.enums import CoreDomain


class BioDict(TypedDict):
    name: str | None
    gender: str | None
    created_at: str | None


class LocationDict(TypedDict):
    current: str
    prev: str | None


class VitalsDict(TypedDict):
    cur: int
    max: int


class StatsDict(TypedDict):
    hp: VitalsDict
    mp: VitalsDict
    stamina: VitalsDict


class AttributesDict(TypedDict):
    strength: int
    agility: int
    endurance: int
    intelligence: int
    wisdom: int
    men: int
    perception: int
    charisma: int
    luck: int


class SessionsDict(TypedDict):
    combat_id: str | None
    inventory_id: str | None
    scenario_id: str | None  # Добавил scenario_id, так как мы его используем


class MetricsDict(TypedDict, total=False):
    """Производные метрики персонажа (gear_score, arena_rating, etc.)."""

    gear_score: int
    arena_rating: int
    arena_wins: int
    arena_losses: int
    win_streak: int


class AccountContextDTO(BaseModel):
    """
    DTO для структуры ac:{char_id} в Redis.
    """

    state: CoreDomain
    prev_state: CoreDomain | None = None  # Добавлено поле
    bio: BioDict
    location: LocationDict
    stats: StatsDict
    attributes: AttributesDict
    sessions: SessionsDict
    metrics: MetricsDict

    # Дополнительные поля (skills, etc.) можно добавить позже
    skills: dict[str, Any] = {}
