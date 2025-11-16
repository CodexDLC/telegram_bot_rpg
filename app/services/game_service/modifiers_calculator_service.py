#app/services/game_service/modifiers_calculator_service.py
from loguru import logger as log
from app.resources.schemas_dto.character_dto import CharacterStatsReadDTO
from app.resources.schemas_dto.modifer_dto import CharacterModifiersSaveDto


class ModifiersCalculatorService:

    @staticmethod
    def calculate_all_modifiers_for_stats(base_stats: CharacterStatsReadDTO) -> CharacterModifiersSaveDto:
        # --- Таблица 1: Физический Блок ---
        physical_damage_bonus = base_stats.strength * (2.5 / 100)
        physical_penetration = base_stats.strength * (1/100)
        physical_crit_chance = base_stats.agility * (1/100)
        dodge_chance = base_stats.agility * (1/100)
        anti_dodge = base_stats.agility * (1/100)
        shield_block_chance = base_stats.agility * (1/100)
        hp_max = base_stats.endurance * 15
        hp_regen = base_stats.endurance * (2/100)
        physical_resistance = base_stats.endurance * (1/100)
        shock_resistance = base_stats.endurance * (1/100)

        # --- Таблица 2: Магический Блок ---
        magical_damage_bonus = base_stats.intelligence * (2.5 / 100)
        magical_penetration = base_stats.intelligence * (1/100)
        magical_crit_chance = base_stats.intelligence * (1.5/100)
        spell_land_chance = base_stats.intelligence * (1/100)
        magical_accuracy = base_stats.intelligence * (1.5/100)
        debuff_avoidance = base_stats.intelligence * (1.5/100)
        energy_max = base_stats.endurance * 10
        energy_regen = base_stats.endurance * (5/100)
        magical_resistance = base_stats.endurance * (1/100)
        control_resistance = base_stats.endurance * (1.5/100)

        # --- Таблица 3: Небоевой Блок ---
        trade_discount = base_stats.luck * (1.5/100)
        pet_ally_power = base_stats.luck * (2.5/100)
        find_loot_chance = base_stats.luck * (1.5/100)
        crafting_critical_chance = base_stats.luck * (1/100)
        skill_gain_bonus = base_stats.luck * (2/100)
        crafting_success_chance = base_stats.luck * (1.5/100)
        inventory_slots_bonus = base_stats.perception * 1

        mods = CharacterModifiersSaveDto(
        # --- Физические боевые модификаторы ---
        physical_damage_bonus=physical_damage_bonus,
        physical_penetration=physical_penetration,
        physical_crit_chance=physical_crit_chance,

        # --- Магические боевые модификаторы ---
        magical_damage_bonus=magical_damage_bonus,
        magical_penetration=magical_penetration,
        magical_crit_chance=magical_crit_chance,

        spell_land_chance=spell_land_chance,
        magical_accuracy=magical_accuracy,

        # --- Общие боевые модификаторы ---
        pet_ally_power=pet_ally_power,

        # --- Ресурсы ---
        hp_max=hp_max,
        hp_regen=hp_regen,
        energy_max=energy_max,
        energy_regen=energy_regen,

        # --- Защитные модификаторы ---
        dodge_chance=dodge_chance,
        anti_dodge=anti_dodge,
        debuff_avoidance=debuff_avoidance,
        shield_block_chance=shield_block_chance,
        shield_block_power=0.0,
        physical_resistance=physical_resistance,
        control_resistance=control_resistance,
        magical_resistance=magical_resistance,
        shock_resistance=shock_resistance,

        # --- Утилитарные и экономические модификаторы ---
        trade_discount=trade_discount,
        find_loot_chance=find_loot_chance,
        crafting_critical_chance=crafting_critical_chance,
        skill_gain_bonus=skill_gain_bonus,
        crafting_success_chance=crafting_success_chance,
        inventory_slots_bonus=inventory_slots_bonus

        )

        return mods