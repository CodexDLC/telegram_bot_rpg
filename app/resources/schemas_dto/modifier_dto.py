# app/resources/schemas_dto/modifier_dto.py
from pydantic import BaseModel


class CharacterModifiersSaveDto(BaseModel):
    """
    DTO для хранения РАССЧИТАННЫХ модификаторов.
    Используется:
    1. В StatsAggregationService (как результат расчетов).
    2. В UI (StatusModifierService) для отображения игроку.
    НЕ ИСПОЛЬЗУЕТСЯ В БОЮ (там CombatSessionContainerDTO).
    """

    # --- Ресурсы ---
    hp_max: int = 0
    hp_regen: float = 0.0
    energy_max: int = 0
    energy_regen: float = 0.0

    # --- Физическая Атака ---
    physical_damage_bonus: float = 0.0
    physical_penetration: float = 0.0
    physical_crit_chance: float = 0.0
    physical_crit_power_float: float = 1.5

    # --- Магическая Атака ---
    magical_damage_bonus: float = 0.0
    magical_penetration: float = 0.0
    magical_crit_chance: float = 0.0
    magical_crit_power_float: float = 1.5
    spell_land_chance: float = 0.0
    magical_accuracy: float = 0.0

    # --- Защита ---
    physical_resistance: float = 0.0
    magical_resistance: float = 0.0
    control_resistance: float = 0.0
    shock_resistance: float = 0.0
    debuff_avoidance: float = 0.0
    dodge_chance: float = 0.0
    anti_dodge: float = 0.0
    shield_block_chance: float = 0.0
    shield_block_power: float = 0.0
    anti_physical_crit_chance: float = 0.0
    anti_magical_crit_chance: float = 0.0

    # --- Общие Боевые ---
    counter_attack_chance: float = 0.0
    pet_ally_power: float = 0.0
    vampiric_rage: float = 0.0
    received_healing_bonus: float = 0.0
    parry_chance: float = 0.0

    # --- Экономика и Утилиты ---
    trade_discount: float = 0.0
    find_loot_chance: float = 0.0
    crafting_critical_chance: float = 0.0
    crafting_success_chance: float = 0.0
    skill_gain_bonus: float = 0.0
    inventory_slots_bonus: int = 0
