from pydantic import BaseModel, Field


class CharacterModifiersSaveDto(BaseModel):
    """
    DTO для хранения рассчитанных модификаторов (Lvl 2).
    Используется в StatsAggregationService и UI.
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


class CombatStatsDTO(CharacterModifiersSaveDto):
    """
    ФИНАЛЬНЫЙ слепок для боя.
    Наследует все модификаторы (Lvl 2) и добавляет базу (Lvl 1) + урон оружия.
    """

    # --- 1. Базовые Характеристики (Base Stats) ---
    strength: int = 0
    agility: int = 0
    endurance: int = 0
    intelligence: int = 0
    wisdom: int = 0
    men: int = 0
    perception: int = 0
    charisma: int = 0
    luck: int = 0

    # --- 2. Урон (Weapon Damage) ---
    phys_damage_min: int = 0
    phys_damage_max: int = 0
    magic_damage_min: int = 0
    magic_damage_max: int = 0


class FighterStateDTO(BaseModel):
    """
    Динамическое состояние бойца в бою (HP, Shield, Tokens).
    """

    hp_current: int

    # ЩИТ = ЭНЕРГИЯ (Energy Shield Mechanic)
    energy_current: int

    # Токены (Накопленные ресурсы приемов)
    # Пример: {"blood": 3, "combo": 1, "rage": 50}
    tokens: dict[str, int] = Field(default_factory=dict)

    # Активные эффекты (Яды, Станы, Баффы)
    # Пример: [{"id": "poison", "stacks": 2, "duration": 3}]
    effects: list[dict] = Field(default_factory=list)


class CombatParticipantDTO(BaseModel):
    """
    Полный объект участника боя, который хранится в Redis.
    """

    char_id: int
    team: str  # "blue" (игроки) / "red" (мобы)
    is_ai: bool  # True для мобов
    name: str  # Имя для логов

    # Ссылка на динамическое состояние
    state: FighterStateDTO

    # Ссылка на полный слепок статов
    stats: CombatStatsDTO
