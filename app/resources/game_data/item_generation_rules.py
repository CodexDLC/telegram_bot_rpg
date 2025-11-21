# Это "Конструктор", из которого мы собираем предмет перед сохранением

BASE_ITEM_TEMPLATES = {
    # --- ОРУЖИЕ ---
    "sword": {
        "type": "weapon",
        "slots": ["main_hand"],
        "damage_range": (3, 6),  # Базовый разброс для Common
        "weight": 2.0,
    },
    "greatsword": {"type": "weapon", "slots": ["two_hand"], "damage_range": (8, 14), "weight": 5.0},
    "dagger": {
        "type": "weapon",
        "slots": ["main_hand", "off_hand"],  # Твой кейс с кинжалом!
        "damage_range": (1, 4),
        "weight": 0.5,
    },
    # --- БРОНЯ ---
    "plate_chest": {"type": "armor", "slots": ["chest"], "protection_base": 10, "weight": 15.0},
}

# Коэффициенты редкости (на что умножаем статы)
RARITY_MULTIPLIERS = {"common": 1.0, "uncommon": 1.2, "rare": 1.5, "epic": 2.0, "legendary": 3.0}

# Правила бонусов (сколько слотов у какой рарности)
BONUS_SLOTS = {"common": 0, "uncommon": 1, "rare": 2, "epic": 3, "legendary": 4}
