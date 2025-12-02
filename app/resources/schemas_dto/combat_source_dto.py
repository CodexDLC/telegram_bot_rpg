# app/resources/schemas_dto/combat_source_dto.py
from typing import Any

from pydantic import BaseModel, Field


class BattleStatsDTO(BaseModel):
    """
    Статистика эффективности бойца за сессию.
    """

    damage_dealt: int = 0  # Нанесено урона (HP)
    damage_taken: int = 0  # Получено урона
    healing_done: int = 0  # Вылечено (себя или других)
    blocks_success: int = 0  # Успешных блоков
    dodges_success: int = 0  # Успешных уворотов
    crits_landed: int = 0  # Критов нанесено
    kills: int = 0  # Убийств


class FighterStateDTO(BaseModel):
    """
    Динамическое состояние бойца.
    """

    hp_current: int
    energy_current: int

    # Очередь целей и заряды смены
    targets: list[int] = Field(default_factory=list)
    switch_charges: int = 0
    max_switch_charges: int = 0

    exchange_count: int = 0

    # Токены (hit, crit, block...)
    tokens: dict[str, int] = Field(default_factory=dict)

    # Временные эффекты
    effects: dict[str, Any] = Field(default_factory=dict)

    # 🔥 НОВОЕ: Статистика внутри состояния
    stats: BattleStatsDTO = Field(default_factory=BattleStatsDTO)

    xp_buffer: dict[str, int] = Field(default_factory=dict)


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

    active_abilities: list[str] = Field(default_factory=list)
    persistent_pipeline: list[str] = Field(default_factory=list)

    state: FighterStateDTO | None = None
    stats: dict[str, StatSourceData] = Field(default_factory=dict)
