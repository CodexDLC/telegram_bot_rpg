# app/resources/schemas_dto/combat_source_dto.py
from typing import Any

from pydantic import BaseModel, Field


class FighterStateDTO(BaseModel):
    """
    Динамическое состояние бойца.
    """

    hp_current: int
    energy_current: int

    # 🔥 НОВОЕ: Индивидуальный счетчик обменов
    exchange_count: int = 0

    tokens: dict[str, int] = Field(default_factory=dict)
    effects: dict[str, Any] = Field(default_factory=dict)


class StatSourceData(BaseModel):
    base: float = 0.0
    equipment: float = 0.0
    skills: float = 0.0
    buffs_flat: dict[str, float] = Field(default_factory=dict)
    buffs_percent: dict[str, float] = Field(default_factory=dict)


class CombatSessionContainerDTO(BaseModel):
    char_id: int
    team: str
    name: str
    is_ai: bool = False
    state: FighterStateDTO | None = None
    stats: dict[str, StatSourceData] = Field(default_factory=dict)
