# app/resources/game_data/ability_data_struct.py
from typing import Any, TypedDict


class AbilityRules(TypedDict, total=False):
    """
    Флаги, которые передаются в CombatCalculator (Pre-Calc).
    """

    ignore_block: bool
    ignore_dodge: bool
    ignore_parry: bool

    bonus_crit: float
    damage_mult: float

    override_damage_type: str


class AbilityPipelineStep(TypedDict):
    """
    Один шаг в конвейере (Post-Calc).
    """

    phase: str
    trigger: str

    action: str
    target: str

    params: dict[str, Any]


class AbilityData(TypedDict):
    """
    Полное описание способности.
    Кулдаунов нет — ограничение только через cost_tactics/cost_energy.
    """

    name: str
    description: str

    # Стоимость
    cost_energy: int
    cost_tactics: int
    cost_hp: int

    # Правила и Пайплайн
    rules: AbilityRules
    pipeline: list[AbilityPipelineStep]
