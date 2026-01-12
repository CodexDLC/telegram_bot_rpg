from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class EffectType(str, Enum):
    DOT = "dot"
    HOT = "hot"
    BUFF = "buff"
    DEBUFF = "debuff"
    CONTROL = "control"


class EffectDTO(BaseModel):
    effect_id: str
    name_en: str
    name_ru: str

    type: EffectType
    duration: int

    # Фиксированное воздействие
    impact_flat: dict[str, int] = Field(default_factory=dict)

    # Динамическое масштабирование
    # {"source": "snapshot_damage", "stat": "hp", "power": 1}
    scaling: dict[str, Any] = Field(default_factory=dict)

    modifiers: dict[str, Any] = Field(default_factory=dict)
    flags: dict[str, Any] = Field(default_factory=dict)

    description: str
