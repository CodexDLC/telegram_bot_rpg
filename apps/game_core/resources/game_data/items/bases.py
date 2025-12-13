from typing import TypedDict


# Описываем строгую структуру словаря, чтобы IDE помогала
class BaseItemData(TypedDict):
    id: str
    name_ru: str  # Название для "Мусорной" версии (Tier 0)
    slot: str  # main_hand, off_hand, body, head, legs, etc.
    damage_type: str | None  # physical, magical (None если это броня)
    defense_type: str | None  # physical, magical (None если это оружие)
    allowed_materials: list[str]  # Ссылка на категории материалов ('ingots', 'leathers')
    base_power: int  # Фундамент силы (Урон или Защита) для множителя x1.0
    base_durability: int  # Фундамент прочности
    narrative_tags: list[str]  # Теги "Формы" для LLM (без качественных прилагательных)


# Основная база данных
# Структура: Категория -> ID Базы -> Данные
BASES_DB: dict[str, dict[str, BaseItemData]] = {
    # === ОРУЖИЕ БЛИЖНЕГО БОЯ ===
    "melee_weapons": {
        "sword": {
            "id": "sword",
            "name_ru": "Ржавый меч",
            "slot": "main_hand",
            "damage_type": "physical",
            "defense_type": None,
            "allowed_materials": ["ingots"],  # Только металлы
            "base_power": 10,  # 10 урона на Tier 1
            "base_durability": 50,
            "narrative_tags": ["sword", "blade", "1h", "melee"],
        },
        "axe": {
            "id": "axe",
            "name_ru": "Тупой топор",
            "slot": "main_hand",
            "damage_type": "physical",
            "defense_type": None,
            "allowed_materials": ["ingots"],
            "base_power": 12,  # Чуть мощнее меча
            "base_durability": 45,  # Но ломается быстрее
            "narrative_tags": ["axe", "chop", "1h", "heavy"],
        },
        "club": {
            "id": "club",
            "name_ru": "Дубина",
            "slot": "main_hand",
            "damage_type": "physical",
            "defense_type": None,
            "allowed_materials": ["woods", "ingots"],  # Дерево или Металл
            "base_power": 15,  # Высокий разовый урон
            "base_durability": 40,
            "narrative_tags": ["club", "blunt", "1h", "smash"],
        },
    },
    # === БРОНЯ ТЕЛА ===
    "body_armor": {
        "shirt": {
            "id": "shirt",
            "name_ru": "Тряпье",
            "slot": "body",
            "damage_type": None,
            "defense_type": "physical",
            "allowed_materials": ["cloths"],  # Только ткани
            "base_power": 2,  # 2 защиты на Tier 1
            "base_durability": 20,
            "narrative_tags": ["clothing", "shirt", "light"],
        },
        "plate_chest": {
            "id": "plate_chest",
            "name_ru": "Гнутая кираса",
            "slot": "body",
            "damage_type": None,
            "defense_type": "physical",
            "allowed_materials": ["ingots"],  # Только металл
            "base_power": 15,  # Высокая защита
            "base_durability": 100,
            "narrative_tags": ["plate", "armor", "heavy", "metal"],
        },
    },
}
