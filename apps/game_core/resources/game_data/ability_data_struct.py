"""
Модуль содержит структуры данных для описания способностей и их эффектов.

Определяет `AbilityRules` (флаги для расчета боя), `AbilityPipelineStep`
(шаги выполнения эффектов способности) и `AbilityData` (полное описание
способности, включая стоимость и пайплайн).
"""

from typing import Any, TypedDict


class AbilityRules(TypedDict, total=False):
    """
    Флаги, которые передаются в CombatCalculator для фазы Pre-Calc.
    """

    ignore_block: bool
    ignore_dodge: bool
    ignore_parry: bool
    bonus_crit: float
    damage_mult: float
    override_damage_type: str


class AbilityPipelineStep(TypedDict):
    """
    Один шаг в конвейере выполнения способности (фаза Post-Calc).
    """

    phase: str
    trigger: str
    action: str
    target: str
    params: dict[str, Any]


class AbilityData(TypedDict):
    """
    Полное описание способности.
    """

    name: str
    description: str
    cost_energy: int
    cost_tactics: int
    cost_hp: int
    rules: AbilityRules
    pipeline: list[AbilityPipelineStep]
