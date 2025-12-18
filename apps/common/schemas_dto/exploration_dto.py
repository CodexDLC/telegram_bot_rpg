# apps/common/schemas_dto/exploration_dto.py
from enum import Enum
from typing import Any

from pydantic import BaseModel


class WorldNavigationDTO(BaseModel):
    loc_id: str
    name: str
    description: str
    exits: dict[str, Any]
    flags: dict[str, Any]
    players_count: int = 0
    active_battles: int = 0
    visual_objects: list[str] = []
    metadata: dict[str, Any] = {}


class EncounterType(str, Enum):
    COMBAT = "COMBAT"
    NARRATIVE = "NARRATIVE"


class DetectionStatus(str, Enum):
    AMBUSH = "AMBUSH"
    DETECTED = "DETECTED"


class EncounterDTO(BaseModel):
    type: EncounterType
    encounter_id: str  # Технический ID (UUID клана или ID события)
    name: str  # Имя для отображения (e.g., "Банда Орков")
    description: str | None = None  # Описание для превью
    status: DetectionStatus | None = None
    mob_tier: int | None = None
    metadata: dict[str, Any] = {}
