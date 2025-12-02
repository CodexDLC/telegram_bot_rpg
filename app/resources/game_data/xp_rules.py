"""
Модуль содержит правила и константы для расчета опыта (XP) в игре.

Определяет базовое количество опыта за действие, сопоставление подтипов
предметов/действий с ключами навыков, а также множители опыта
в зависимости от исхода действия (успех, крит, промах и т.д.).
"""

BASE_ACTION_XP = 10

XP_SOURCE_MAP = {
    "sword": "melee_combat",
    "axe": "melee_combat",
    "mace": "melee_combat",
    "dagger": "melee_combat",
    "spear": "melee_combat",
    "unarmed": "melee_combat",
    "bow": "ranged_combat",
    "crossbow": "ranged_combat",
    "staff": "magical_damage_bonus",
    "heavy": "heavy_armor",
    "medium": "medium_armor",
    "light": "light_armor",
    "shield": "shield",
    "pickaxe": "mining",
    "hatchet": "woodcutting",
    "hammer": "armor_craft",
}

OUTCOME_MULTIPLIERS = {
    "crit": 3.0,
    "success": 2.0,
    "partial": 1.0,
    "fail": 0.5,
    "miss": 0.0,
}
