from typing import Any

from pydantic import BaseModel, Field


class TriggerDTO(BaseModel):
    trigger_id: str
    weapon_class: str

    event: str
    flag_name: str
    effect_id: str | None

    mutations: dict[str, Any] = Field(default_factory=dict)

    description: str
