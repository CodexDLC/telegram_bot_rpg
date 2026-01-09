"""
DTO для управления Пайплайном Боя (Combat Pipeline).
Содержит флаги, контексты и результаты расчетов.
"""

from typing import Literal

from pydantic import BaseModel, Field

# ==============================================================================
# 1. FLAGS & SWITCHES (Управление логикой)
# ==============================================================================


class PipelinePhasesDTO(BaseModel):
    """Управление глобальными фазами пайплайна."""

    run_pre_calc: bool = True
    run_calculator: bool = True
    run_post_calc: bool = True

    is_target_dead: bool = False
    is_interrupted: bool = False


class ForceFlagsDTO(BaseModel):
    """Абсолютные переключатели результата."""

    hit: bool = False
    miss: bool = False
    crit: bool = False
    dodge: bool = False
    parry: bool = False
    block: bool = False
    hit_evasion: bool = False


class RestrictionFlagsDTO(BaseModel):
    """Запреты."""

    cannot_crit: bool = False
    ignore_parry: bool = False
    ignore_block: bool = False


class MasteryFlagsDTO(BaseModel):
    """Флаги мастерства."""

    light_armor: bool = False
    medium_armor: bool = False
    shield_reflect: bool = False
    unarmed_combo: bool = False


class FormulaFlagsDTO(BaseModel):
    """Переключатели формул."""

    # Evasion
    evasion_halved: bool = False
    ignore_evasion_cap: bool = False
    zero_anti_evasion: bool = False

    # Parry/Block
    parry_halved: bool = False
    ignore_parry_cap: bool = False
    block_halved: bool = False
    ignore_block_cap: bool = False

    # Crit
    crit_ignore_anticrit: bool = False

    # Damage
    can_pierce: bool = False  # Разрешить проверку на пронзание


class DamageTypeFlagsDTO(BaseModel):
    """Типы урона."""

    physical: bool = True
    pure: bool = False
    fire: bool = False
    water: bool = False
    air: bool = False
    earth: bool = False
    light: bool = False
    darkness: bool = False
    arcane: bool = False
    nature: bool = False


class StateFlagsDTO(BaseModel):
    """Внутреннее состояние."""

    partial_absorb_reflect: bool = False
    is_reflect_block: bool = False
    open_combo: bool = False
    hit_index: int = 0


class PipelineFlagsDTO(BaseModel):
    """Группировка всех флагов."""

    force: ForceFlagsDTO = Field(default_factory=ForceFlagsDTO)
    restriction: RestrictionFlagsDTO = Field(default_factory=RestrictionFlagsDTO)
    mastery: MasteryFlagsDTO = Field(default_factory=MasteryFlagsDTO)
    formula: FormulaFlagsDTO = Field(default_factory=FormulaFlagsDTO)
    damage: DamageTypeFlagsDTO = Field(default_factory=DamageTypeFlagsDTO)
    state: StateFlagsDTO = Field(default_factory=StateFlagsDTO)

    enable_counter: bool = False
    can_counter_on_parry: bool = False


# ==============================================================================
# 2. MODIFIERS & TRIGGERS (Данные)
# ==============================================================================


class PipelineModsDTO(BaseModel):
    """Числовые модификаторы."""

    accuracy_mult: float = 1.0


class PipelineTriggersDTO(BaseModel):
    """Флаги активации триггеров."""

    trigger_combo: bool = False
    trigger_stun: bool = False
    trigger_counter_dodge: bool = False


class PipelineStagesDTO(BaseModel):
    """Управление этапами."""

    check_accuracy: bool = True
    check_evasion: bool = True
    check_parry: bool = True
    check_block: bool = True
    check_crit: bool = True
    calculate_damage: bool = True


# ==============================================================================
# 3. CONTEXT & RESULT (Вход и Выход)
# ==============================================================================


class PipelineContextDTO(BaseModel):
    """Пульт управления боем."""

    phases: PipelinePhasesDTO = Field(default_factory=PipelinePhasesDTO)
    flags: PipelineFlagsDTO = Field(default_factory=PipelineFlagsDTO)
    mods: PipelineModsDTO = Field(default_factory=PipelineModsDTO)
    triggers: PipelineTriggersDTO = Field(default_factory=PipelineTriggersDTO)
    stages: PipelineStagesDTO = Field(default_factory=PipelineStagesDTO)

    # Meta
    source_type: Literal["main_hand", "off_hand", "magic", "item"] = "main_hand"
    override_damage: tuple[float, float] | None = None

    # Calc Flags
    can_counter: bool = True


class InteractionResultDTO(BaseModel):
    """Итоговый отчет."""

    is_hit: bool = False
    is_crit: bool = False
    is_blocked: bool = False
    is_parried: bool = False
    is_dodged: bool = False
    is_miss: bool = False
    is_counter: bool = False

    crit_mult: float = 1.0

    damage_raw: int = 0
    damage_mitigated: int = 0
    damage_final: int = 0
    reflected_damage: int = 0

    tokens_awarded_attacker: list[str] = Field(default_factory=list)
    tokens_awarded_defender: list[str] = Field(default_factory=list)
