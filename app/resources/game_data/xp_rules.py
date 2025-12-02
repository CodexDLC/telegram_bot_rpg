# app/resources/game_data/xp_rules.py

# Базовый опыт за любое успешное "усилие" (удар, блок, крафт)
# Это "сырые" очки, которые потом умножаются на Рейт персонажа.
BASE_ACTION_XP = 10

# 1. СВЯЗЬ: ПОДТИП ПРЕДМЕТА -> КЛЮЧ НАВЫКА
# Мы смотрим на поле 'subtype' у предмета (sword, shield, heavy_armor).
# Если subtype нет в этом списке, опыт не начисляется.
XP_SOURCE_MAP = {
    # --- ОРУЖИЕ (Атака) ---
    "sword": "melee_combat",
    "axe": "melee_combat",
    "mace": "melee_combat",
    "dagger": "melee_combat",  # Можно разделить позже
    "spear": "melee_combat",
    "unarmed": "melee_combat",  # Если кулаки
    "bow": "ranged_combat",
    "crossbow": "ranged_combat",
    "staff": "magical_damage_bonus",  # Или отдельная школа
    # --- БРОНЯ (Получение урона) ---
    "heavy": "heavy_armor",
    "medium": "medium_armor",
    "light": "light_armor",
    # --- ЩИТ (Блокирование) ---
    "shield": "shield",
    # --- ИНСТРУМЕНТЫ (Мирные действия - задел на будущее) ---
    "pickaxe": "mining",
    "hatchet": "woodcutting",
    "hammer": "armor_craft",
}

# 2. МНОЖИТЕЛИ ИСХОДА (Outcome)
# На это число умножается BASE_ACTION_XP.
OUTCOME_MULTIPLIERS = {
    "crit": 3.0,  # Критический успех (Крит удар)
    "success": 2.0,  # Обычный успех (Попадание / Получение урона броней)
    "partial": 1.0,  # Частичный успех (Удар в блок / Блок щитом)
    "fail": 0.5,  # Неудача, но опыт идет (Парировали / Увернулись)
    "miss": 0.0,  # Полный промах (нет опыта)
}
