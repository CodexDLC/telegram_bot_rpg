"""
Модуль содержит правила и шаблоны для генерации игровых предметов.

Определяет базовые характеристики для различных типов предметов (оружие, броня),
коэффициенты редкости, влияющие на их силу, и количество бонусных слотов
в зависимости от редкости предмета.
"""

BASE_ITEM_TEMPLATES = {
    "sword": {
        "type": "weapon",
        "slots": ["main_hand"],
        "damage_range": (3, 6),
        "weight": 2.0,
    },
    "greatsword": {"type": "weapon", "slots": ["two_hand"], "damage_range": (8, 14), "weight": 5.0},
    "dagger": {
        "type": "weapon",
        "slots": ["main_hand", "off_hand"],
        "damage_range": (1, 4),
        "weight": 0.5,
    },
    "plate_chest": {"type": "armor", "slots": ["chest"], "protection_base": 10, "weight": 15.0},
}

RARITY_MULTIPLIERS = {"common": 1.0, "uncommon": 1.2, "rare": 1.5, "epic": 2.0, "legendary": 3.0}

BONUS_SLOTS = {"common": 0, "uncommon": 1, "rare": 2, "epic": 3, "legendary": 4}
