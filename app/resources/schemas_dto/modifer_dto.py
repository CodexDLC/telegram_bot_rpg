# app/resources/schemas_dto/modifier_dto.py
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class CharacterModifiersDto(BaseModel):
    """
    DTO для модели CharacterModifiers.

    Используется для валидации данных и их безопасной передачи
    между различными частями приложения. Поля соответствуют
    ORM-модели `CharacterModifiers`.
    """
    character_id: int

    # --- Физические боевые модификаторы ---
    physical_damage_bonus: float
    physical_penetration: float
    physical_crit_chance: float
    physical_crit_power_float: float
    physical_crit_power_int: int
    physical_crit_chance_cap: float

    # --- Магические боевые модификаторы ---
    magical_damage_bonus: float
    magical_penetration: float
    magical_crit_chance: float
    magical_crit_power_float: float
    magical_crit_power_int: int
    magical_crit_chance_cap: float
    spell_land_chance: float
    magical_accuracy: float

    # --- Общие боевые модификаторы ---
    counter_attack_chance: float
    pet_ally_power: float
    vampiric_rage: float
    parry_chance: float

    # --- Ресурсы ---
    hp_max: int
    hp_regen: float
    energy_max: int
    energy_regen: float

    # --- Защитные модификаторы ---
    dodge_chance: float
    anti_dodge: float
    debuff_avoidance: float
    shield_block_chance: float
    shield_block_power: float
    physical_resistance: float
    control_resistance: float
    magical_resistance: float
    anti_physical_crit_chance: float
    anti_magical_crit_chance: float
    shock_resistance: float

    # --- Экипировка (может быть не надета) ---
    armor_shield: Optional[str] = None
    armor_head: Optional[str] = None
    armor_chest: Optional[str] = None
    armor_legs: Optional[str] = None
    armor_feet: Optional[str] = None

    # --- Утилитарные и экономические модификаторы ---
    received_healing_bonus: float
    trade_discount: float
    find_loot_chance: float
    crafting_critical_chance: float
    skill_gain_bonus: float
    crafting_success_chance: float
    inventory_slots_bonus: int

    # --- Временные метки ---
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CharacterModifiersSaveDto(BaseModel):
    """
    DTO для СОХРАНЕНИЯ/ОБНОВЛЕНИЯ CharacterModifiers.
    Содержит ТОЛЬКО модификаторы, рассчитанные из Lvl 1 Статов.
    """
    # --- Таблица 1: Физический Блок ---
    physical_damage_bonus: float
    physical_penetration: float
    shield_block_power: float
    physical_crit_chance: float
    dodge_chance: float
    anti_dodge: float
    shield_block_chance: float
    hp_max: int
    hp_regen: float
    physical_resistance: float
    shock_resistance: float

    # --- Таблица 2: Магический Блок ---
    magical_damage_bonus: float
    magical_penetration: float
    spell_land_chance: float
    magical_crit_chance: float
    magical_accuracy: float
    debuff_avoidance: float
    energy_max: int
    energy_regen: float
    magical_resistance: float
    control_resistance: float

    # --- Таблица 3: Небоевой Блок ---
    trade_discount: float
    pet_ally_power: float
    find_loot_chance: float
    crafting_critical_chance: float
    skill_gain_bonus: float
    crafting_success_chance: float
    inventory_slots_bonus: int