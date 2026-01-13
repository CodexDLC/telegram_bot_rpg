"""
DTO, описывающие состояние Актора (Участника боя).
"""

from typing import Any

from pydantic import BaseModel, Field

from apps.common.schemas_dto.modifier_dto import (
    CombatModifiersDTO,
    CombatSkillsDTO,
)


class ActorMetaDTO(BaseModel):
    """
    Мета-данные и Состояние (State).
    Соответствует ключу `meta` в Redis JSON.
    """

    # Identity
    id: str | int
    name: str
    type: str  # "player", "monster"
    team: str
    template_id: str | None = None
    is_ai: bool = False

    # State (Hot Data)
    hp: int = 0
    max_hp: int = 0
    en: int = 0
    max_en: int = 0
    tactics: int = 0
    is_dead: bool = False
    afk_level: int = 0
    tokens: dict[str, int] = Field(default_factory=dict)


class ActorRawDTO(BaseModel):
    """
    Математическая модель (Cold Data).
    Соответствует ключу `raw` в Redis JSON.
    """

    attributes: dict[str, Any] = Field(default_factory=dict)
    modifiers: dict[str, Any] = Field(default_factory=dict)


class ActorLoadoutDTO(BaseModel):
    """
    Экипировка и доступные действия.
    Соответствует ключу `loadout` в Redis JSON.
    """

    layout: dict[str, str] = Field(default_factory=dict)  # {slot: skill_key}
    belt: list[dict[str, Any]] = Field(default_factory=list)
    known_abilities: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class ActiveAbilityDTO(BaseModel):
    """
    Активные эффекты из Redis JSON `:active_abilities`.
    Dynamic Modifiers.
    """

    uid: str
    ability_id: str
    source_id: int
    expire_at_exchange: int  # Таймер жизни (в разменах)
    impact: dict[str, int] = Field(default_factory=dict)  # {"hp": -10}
    payload: dict[str, Any] = Field(default_factory=dict)


class ActorStats(BaseModel):
    """
    Готовые статы для математики (In-Memory Calculated).
    Композиция: Модификаторы (результат калькулятора) + Скиллы (из базы).
    """

    calculated_at: float = 0.0

    # 1. Результат WaterfallCalculator (Чистые цифры, включая StatusStats)
    mods: CombatModifiersDTO = Field(default_factory=CombatModifiersDTO)

    # 2. Скиллы (из Redis/Snapshot)
    skills: CombatSkillsDTO = Field(default_factory=CombatSkillsDTO)

    @classmethod
    def from_flat_dict(cls, flat_data: dict[str, Any]) -> "ActorStats":
        """
        Фабрика для создания ActorStats из плоского словаря.
        """
        mods_data = {}
        skills_data = {}

        mods_fields = CombatModifiersDTO.model_fields.keys()
        skills_fields = CombatSkillsDTO.model_fields.keys()

        for key, value in flat_data.items():
            if key in skills_fields:
                skills_data[key] = value
            elif key in mods_fields:
                mods_data[key] = value

        return cls(
            mods=CombatModifiersDTO(**mods_data),
            skills=CombatSkillsDTO(**skills_data),
        )


class ActorSnapshot(BaseModel):
    """
    Агрегатор данных актера в памяти.
    Точная копия структуры Redis JSON.
    """

    # 1. Meta & State
    meta: ActorMetaDTO

    # 2. Math Model Source
    raw: ActorRawDTO

    # 3. Skills Source
    skills: dict[str, float] = Field(default_factory=dict)

    # 4. Loadout & Config
    loadout: ActorLoadoutDTO = Field(default_factory=ActorLoadoutDTO)

    # 5. Dynamic
    active_abilities: list[ActiveAbilityDTO] = Field(default_factory=list)
    xp_buffer: dict[str, int] = Field(default_factory=dict)

    # 6. Analytics & Debug
    metrics: dict[str, float] = Field(default_factory=dict)
    explanation: dict[str, str] = Field(default_factory=dict)

    # --- Calculated (In-Memory only) ---
    stats: ActorStats | None = None
    dirty_stats: set[str] = Field(default_factory=set)

    # --- Helpers ---
    @property
    def char_id(self) -> int:
        return int(self.meta.id)

    @property
    def team(self) -> str:
        return self.meta.team

    @property
    def is_alive(self) -> bool:
        return not self.meta.is_dead and self.meta.hp > 0

    @property
    def state(self) -> ActorMetaDTO:
        return self.meta
