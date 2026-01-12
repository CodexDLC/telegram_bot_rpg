from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AbilityType(str, Enum):
    INSTANT = "instant"
    REACTION = "reaction"
    PASSIVE = "passive"


class AbilitySource(str, Enum):
    GIFT = "gift"
    COMBAT = "combat"


class AbilityTarget(str, Enum):
    SELF = "self"
    SINGLE_ENEMY = "single_enemy"
    ALL_ENEMIES = "all_enemies"
    SINGLE_ALLY = "single_ally"
    ALL_ALLIES = "all_allies"


class EffectConfig(BaseModel):
    trigger: str
    action: str
    params: dict[str, Any]


class AbilityDTO(BaseModel):
    ability_id: str
    name_en: str
    name_ru: str

    type: AbilityType
    source: AbilitySource
    target: AbilityTarget

    cost_energy: int = 0
    cost_hp: int = 0
    cost_tokens: dict[str, int] = Field(default_factory=dict)

    flags: dict[str, Any] = Field(default_factory=dict)
    effects: list[EffectConfig] = Field(default_factory=list)

    description: str
