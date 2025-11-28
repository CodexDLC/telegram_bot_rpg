# app/resources/schemas_dto/modifier_dto.py
from pydantic import BaseModel, ConfigDict


class CharacterModifiersSaveDto(BaseModel):
    """
    Глобальное хранилище всех возможных модификаторов персонажа.
    Используется для расчетов, UI и передачи данных в бой.

    Structure:
    1. Resources (HP/Energy)
    2. Physical Offense (Melee/Ranged)
    3. Magical Offense (Cast)
    4. Defense (Mitigation/Avoidance)
    5. Elemental & Status Types (Fire, Poison, Bleed...)
    6. Utility (Economy/Craft)
    """

    # Запрещаем лишние поля, чтобы ловить опечатки при разработке
    model_config = ConfigDict(extra="forbid")

    # ==========================================================================
    # 1. ❤️ РЕСУРСЫ (Vitals)
    # ==========================================================================
    hp_max: int = 0
    hp_regen: float = 0.0  # Flat regen per tick
    energy_max: int = 0
    energy_regen: float = 0.0  # Flat regen per tick

    # Расход ресурсов (Manacost reduction)
    resource_cost_reduction: float = 0.0  # % снижения затрат

    # ==========================================================================
    # 2. ⚔️ ФИЗИЧЕСКАЯ АТАКА (Physical)
    # ==========================================================================
    # Базовый урон (от оружия + силы)
    physical_damage_min: float = 0.0
    physical_damage_max: float = 0.0

    # % Увеличения физ урона (Mod Damage)
    physical_damage_bonus: float = 0.0

    # Пробивание брони (Ignore Def)
    physical_penetration: float = 0.0

    # Точность (снижает уворот врага)
    physical_accuracy: float = 0.0

    # Крит
    physical_crit_chance: float = 0.0
    physical_crit_power_float: float = 1.5  # Множитель (x1.5 по дефолту)

    # Удар сквозь броню (True Damage chance)
    physical_pierce_chance: float = 0.0

    # 🔥 Кап Физ. Крита (по умолчанию 75%)
    physical_crit_cap: float = 0.75

    # ==========================================================================
    # 3. 🔮 МАГИЧЕСКАЯ АТАКА (Magical)
    # ==========================================================================
    # Сила магии (Flat бонус ко всем спеллам)
    magical_damage_power: float = 0.0

    # % Увеличения маг урона
    magical_damage_bonus: float = 0.0

    # Пробивание маг защиты
    magical_penetration: float = 0.0

    # Магическая точность (Шанс прохождения дебаффа)
    magical_accuracy: float = 0.0

    # Шанс наложения заклинания (устаревающее, но оставим для совместимости)
    spell_land_chance: float = 0.0

    # Магический крит
    magical_crit_chance: float = 0.0
    magical_crit_power_float: float = 1.5

    # 🔥 Кап Маг. Крита
    magical_crit_cap: float = 0.75

    # ==========================================================================
    # 4. 🛡️ ЗАЩИТА И ВЫЖИВАНИЕ (Defense)
    # ==========================================================================
    # Прямое снижение урона (Armor/Resist)
    physical_resistance: float = 0.0
    magical_resistance: float = 0.0

    # Плоское снижение (Damage Reduction Flat)
    damage_reduction_flat: float = 0.0

    # 🔥 Кап Резистов (чтобы нельзя было собрать 100% иммун)
    resistance_cap: float = 0.85

    # Активная защита (Avoidance)
    dodge_chance: float = 0.0  # Уворот
    dodge_cap: float = 0.75  # 🔥 Кап Уворота

    parry_chance: float = 0.0  # Парирование
    parry_cap: float = 0.50  # 🔥 Кап Парирования

    # Блок Щитом
    shield_block_chance: float = 0.0  # Шанс заблокировать
    shield_block_power: float = 0.0  # % поглощения урона при блоке
    shield_block_cap: float = 0.75  # 🔥 Кап Блока

    # Анти-статы (Counter-stats)
    anti_crit_chance: float = 0.0  # Снижает шанс крита по нам
    anti_dodge_chance: float = 0.0  # Снижает уворот врага

    anti_physical_crit_chance: float = 0.0
    anti_magical_crit_chance: float = 0.0

    # Сопротивление контролю
    control_resistance: float = 0.0  # Стан, сон, страх
    shock_resistance: float = 0.0  # Оглушение

    # ==========================================================================
    # 5. 🔥 СТИХИИ И ТИПЫ УРОНА (Elemental Mastery)
    # ==========================================================================

    # --- ОГОНЬ (Fire) ---
    fire_damage_bonus: float = 0.0
    fire_resistance: float = 0.0

    # --- ВОДА / ЛЕД (Water) ---
    water_damage_bonus: float = 0.0
    water_resistance: float = 0.0

    # --- ВОЗДУХ / МОЛНИЯ (Air) ---
    air_damage_bonus: float = 0.0
    air_resistance: float = 0.0

    # --- ЗЕМЛЯ (Earth) ---
    earth_damage_bonus: float = 0.0
    earth_resistance: float = 0.0

    # --- СВЕТ (Light) ---
    light_damage_bonus: float = 0.0
    light_resistance: float = 0.0

    # --- ТЬМА (Darkness) ---
    dark_damage_bonus: float = 0.0
    dark_resistance: float = 0.0

    # --- ЯД (Poison) ---
    poison_damage_bonus: float = 0.0  # Усиливает урон от отравления
    poison_resistance: float = 0.0  # Снижает урон от ядов
    poison_efficiency: float = 0.0  # Увеличивает длительность/шанс яда

    # --- КРОВОТЕЧЕНИЕ (Bleed) ---
    bleed_damage_bonus: float = 0.0
    bleed_resistance: float = 0.0

    # ==========================================================================
    # 6. ✨ СПЕЦИАЛЬНЫЕ БОЕВЫЕ (Special)
    # ==========================================================================
    counter_attack_chance: float = 0.0  # Шанс ударить в ответ при увороте

    # Вампиризм
    vampiric_power: float = 0.0  # % от урона в HP
    vampiric_trigger_chance: float = 0.0

    # Лечение
    healing_power: float = 0.0  # Бонус к исходящему хилу
    received_healing_bonus: float = 0.0  # Бонус к входящему хилу

    # Саммоны (Питомцы)
    pet_damage_bonus: float = 0.0
    pet_health_bonus: float = 0.0

    # ==========================================================================
    # 7. 💰 ЭКОНОМИКА И МИР (Utility)
    # ==========================================================================
    trade_discount: float = 0.0  # Скидка у NPC
    find_loot_chance: float = 0.0  # Magic Find

    # Крафт
    crafting_success_chance: float = 0.0
    crafting_critical_chance: float = 0.0
    crafting_speed: float = 0.0

    # Прокачка
    skill_gain_bonus: float = 0.0  # +% к опыту

    # Инвентарь
    inventory_slots_bonus: int = 0  # +N слотов
    weight_limit_bonus: float = 0.0  # +N кг
