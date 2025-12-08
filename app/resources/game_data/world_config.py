"""
Конфигурация географии мира: Якоря, Палитры биомов и Статика.
Источники данных для генерации тегов.
"""

from typing import Any, TypedDict

# ==============================================================================
# 1. ГЛОБАЛЬНАЯ ГЕОМЕТРИЯ
# ==============================================================================
WORLD_WIDTH = 105
WORLD_HEIGHT = 105
SECTOR_SIZE = 15  # Размер Региона (15x15)
ZONE_SIZE = 5  # Размер Локации внутри Региона (5x5)

# Центр Хаба (D4)
HUB_CENTER: dict[str, int] = {"x": 52, "y": 52}

# Маппинг рядов для ID (A1..G7)
SECTOR_ROWS: list[str] = ["A", "B", "C", "D", "E", "F", "G"]


# ==============================================================================
# 2. ЯКОРЯ СТИХИЙ (ANCHORS)
# Источник Глобальных тегов (влияют на весь Регион).
# ==============================================================================
class AnchorData(TypedDict):
    x: int
    y: int
    power: float
    falloff: float
    type: str
    narrative_tags: list[str]


ANCHORS: list[AnchorData] = [
    # --- СЕВЕР (A4): Лед, Стазис ---
    {
        "x": 7,
        "y": 52,
        "power": 1.2,
        "falloff": 0.08,
        "type": "north_prime",
        "narrative_tags": ["frozen", "ice_crystals", "ancient_tech", "stasis"],
    },
    # --- ЮГ (G4): Огонь, Пепел ---
    {
        "x": 97,
        "y": 52,
        "power": 1.2,
        "falloff": 0.08,
        "type": "south_prime",
        "narrative_tags": ["magma", "ash", "scorched_earth", "smoke"],
    },
    # --- ЗАПАД (D1): Гравитация, Шторм ---
    {
        "x": 52,
        "y": 7,
        "power": 1.2,
        "falloff": 0.08,
        "type": "west_prime",
        "narrative_tags": ["zero_gravity", "floating_rocks", "storm", "lightning"],
    },
    # --- ВОСТОК (D7): Биомасса, Яд ---
    {
        "x": 52,
        "y": 97,
        "power": 1.2,
        "falloff": 0.08,
        "type": "east_prime",
        "narrative_tags": ["biomass", "giant_roots", "poison_spores", "mutation"],
    },
]

PORTAL_PARAMS = {"power": 2.0, "falloff": 0.04}


# ==============================================================================
# 3. ГРАДИЕНТЫ ТЕГОВ (THE GRADIENTS)
# ==============================================================================
# Вместо статических палитр мы используем динамические наборы тегов,
# зависящие от Уровня Угрозы (Tier) в конкретной точке.
# Tier рассчитывается в ThreatService (0..7).

INFLUENCE_TAGS = {
    # --- СЕВЕР (ЛЕД) ---
    "ice": {
        # Периферия (холодно, иней)
        (1, 2): ["frost", "cold_wind", "dead_grass", "brittle_ground"],
        # Глубина (сугробы, лед)
        (3, 4): ["deep_snow", "frozen_trees", "ice_shards", "blizzard"],
        # Эпицентр (абсолютный ноль)
        (5, 7): ["absolute_zero", "time_stasis", "floating_ice", "crystal_structures"],
    },
    # --- ЮГ (ОГОНЬ) ---
    "fire": {
        (1, 2): ["dry_heat", "ash_dust", "cracked_earth", "smell_of_sulfur"],
        (3, 4): ["smoking_craters", "burning_ground", "lava_streams", "black_smoke"],
        (5, 7): ["magma_ocean", "fire_storms", "obsidian_spikes", "melting_reality"],
    },
    # --- ЗАПАД (ГРАВИТАЦИЯ) ---
    "gravity": {
        (1, 2): ["static_electricity", "dust_devils", "low_gravity_pockets"],
        (3, 4): ["floating_rocks", "constant_lightning", "shattered_earth"],
        (5, 7): ["void_rifts", "inverted_gravity", "reality_tears", "storm_wall"],
    },
    # --- ВОСТОК (БИО) ---
    "bio": {
        (1, 2): ["strange_plants", "spores", "moss", "insects"],
        (3, 4): ["giant_mushrooms", "living_vines", "acid_pools", "toxic_fog"],
        (5, 7): ["flesh_landscape", "giant_beating_hearts", "hive_mind", "mutation_source"],
    },
}

# ==============================================================================
# 4. ЗОНЫ СМЕШИВАНИЯ (DIAGONAL OVERLAPS)
# ==============================================================================
# Теги, которые добавляются, если в точке сильно влияние ДВУХ стихий.
# (Рассчитывается в ThreatService: если power_1 > X и power_2 > X)

HYBRID_TAGS = {
    # Север (Лед) + Запад (Гравитация) = Ледяной Шторм
    frozenset(["ice", "gravity"]): ["hail_storm", "frozen_lightning", "shattering_sky"],
    # Север (Лед) + Восток (Био) = Крио-Сон / Сохранение
    frozenset(["ice", "bio"]): ["preserved_corpses", "frozen_flowers", "hibernate"],
    # Юг (Огонь) + Запад (Гравитация) = Плазменный Шторм
    frozenset(["fire", "gravity"]): ["plasma_arcs", "flying_lava", "solar_flare"],
    # Юг (Огонь) + Восток (Био) = Гниение / Болото (Тепло + Влага)
    frozenset(["fire", "bio"]): ["boiling_swamp", "rotting_flesh", "steam", "disease"],
}


# ==============================================================================
# 5. СТАТИЧНЫЕ ЛОКАЦИИ
# ==============================================================================
class _StaticLocationContent(TypedDict):
    title: str
    description: str
    environment_tags: list[str]


class _StaticLocation(TypedDict):
    sector_id: str
    is_active: bool
    service_object_key: str | None
    flags: dict[str, Any]
    content: _StaticLocationContent


STATIC_LOCATIONS: dict[tuple[int, int], _StaticLocation] = {
    # ---------------------------------------------------------
    # ЦЕНТР И ОСИ (КРЕСТ)
    # ---------------------------------------------------------
    (52, 52): {
        "sector_id": "D4",
        "is_active": True,
        "service_object_key": None,
        "flags": {"is_safe_zone": True, "is_hub": True},
        "content": {
            "title": "Портальный Круг",
            "description": "Центр лагеря. Древние камни гудят от магии.",
            "environment_tags": ["portal"],
        },
    },
    # Дороги (Пустыри под застройку)
    (52, 51): {
        "sector_id": "D4",
        "is_active": True,
        "service_object_key": None,
        "flags": {"is_safe_zone": True},
        "content": {"title": "Северная Улица", "description": "Дорога к плацу.", "environment_tags": ["road"]},
    },
    (52, 53): {
        "sector_id": "D4",
        "is_active": True,
        "service_object_key": None,
        "flags": {"is_safe_zone": True},
        "content": {"title": "Южная Улица", "description": "Дорога к таверне.", "environment_tags": ["road"]},
    },
    (51, 52): {
        "sector_id": "D4",
        "is_active": True,
        "service_object_key": None,
        "flags": {"is_safe_zone": True},
        "content": {"title": "Западный Тракт", "description": "Дорога к штабу.", "environment_tags": ["road"]},
    },
    (53, 52): {
        "sector_id": "D4",
        "is_active": True,
        "service_object_key": None,
        "flags": {"is_safe_zone": True},
        "content": {"title": "Восточный Проулок", "description": "Путь к рынку.", "environment_tags": ["road"]},
    },
    # ---------------------------------------------------------
    # ЗДАНИЯ (ПО УГЛАМ ВНУТРИ СТЕН)
    # ---------------------------------------------------------
    (51, 51): {
        "sector_id": "D4",
        "is_active": True,
        "service_object_key": "svc_arena_main",
        "flags": {"is_safe_zone": True},
        "content": {"title": "Ангар Арены", "description": "Зона боев.", "environment_tags": ["arena"]},
    },
    (53, 51): {
        "sector_id": "D4",
        "is_active": True,
        "service_object_key": "market_hub",
        "flags": {"is_safe_zone": True},
        "content": {"title": "Рынок", "description": "Торговые ряды.", "environment_tags": ["market"]},
    },
    (51, 53): {
        "sector_id": "D4",
        "is_active": True,
        "service_object_key": "town_hall_hub",
        "flags": {"is_safe_zone": True},
        "content": {"title": "Ратуша", "description": "Администрация.", "environment_tags": ["official"]},
    },
    (53, 53): {
        "sector_id": "D4",
        "is_active": True,
        "service_object_key": "taverna_hub",
        "flags": {"is_safe_zone": True},
        "content": {"title": "Таверна", "description": "Еда и отдых.", "environment_tags": ["tavern"]},
    },
    # ---------------------------------------------------------
    # ПЕРИМЕТР - СЕВЕРНАЯ ЛИНИЯ (Y=50)
    # ---------------------------------------------------------
    (50, 50): {
        "sector_id": "D4",
        "is_active": True,
        "service_object_key": None,
        "flags": {"is_safe_zone": True, "restricted_exits": ["north", "west"]},
        "content": {"title": "Угол Стены", "description": "Тупик. За стеной виден ров.", "environment_tags": ["wall"]},
    },
    (51, 50): {
        "sector_id": "D4",
        "is_active": True,
        "service_object_key": None,
        "flags": {"is_safe_zone": True, "restricted_exits": ["north"]},
        "content": {"title": "Северная Стена", "description": "Бревенчатый частокол.", "environment_tags": ["wall"]},
    },
    (52, 50): {
        "sector_id": "D4",
        "is_active": True,
        "service_object_key": None,
        "flags": {"is_safe_zone": False, "is_gate": True},
        "content": {"title": "Северные Ворота", "description": "Выход из города.", "environment_tags": ["gate"]},
    },
    (53, 50): {
        "sector_id": "D4",
        "is_active": True,
        "service_object_key": None,
        "flags": {"is_safe_zone": True, "restricted_exits": ["north"]},
        "content": {"title": "Северная Стена", "description": "Бревенчатый частокол.", "environment_tags": ["wall"]},
    },
    (54, 50): {
        "sector_id": "D4",
        "is_active": True,
        "service_object_key": None,
        "flags": {"is_safe_zone": True, "restricted_exits": ["north", "east"]},
        "content": {"title": "Угол Стены", "description": "Тупик.", "environment_tags": ["wall"]},
    },
    # ---------------------------------------------------------
    # ПЕРИМЕТР - ЮЖНАЯ ЛИНИЯ (Y=54)
    # ---------------------------------------------------------
    (50, 54): {
        "sector_id": "D4",
        "is_active": True,
        "service_object_key": None,
        "flags": {"is_safe_zone": True, "restricted_exits": ["south", "west"]},
        "content": {"title": "Угол Стены", "description": "Тупик.", "environment_tags": ["wall"]},
    },
    (51, 54): {
        "sector_id": "D4",
        "is_active": True,
        "service_object_key": None,
        "flags": {"is_safe_zone": True, "restricted_exits": ["south"]},
        "content": {"title": "Южная Стена", "description": "Укрепления.", "environment_tags": ["wall"]},
    },
    (52, 54): {
        "sector_id": "D4",
        "is_active": True,
        "service_object_key": None,
        "flags": {"is_safe_zone": False, "is_gate": True},
        "content": {"title": "Южные Ворота", "description": "Выход к болотам.", "environment_tags": ["gate"]},
    },
    (53, 54): {
        "sector_id": "D4",
        "is_active": True,
        "service_object_key": None,
        "flags": {"is_safe_zone": True, "restricted_exits": ["south"]},
        "content": {"title": "Южная Стена", "description": "Укрепления.", "environment_tags": ["wall"]},
    },
    (54, 54): {
        "sector_id": "D4",
        "is_active": True,
        "service_object_key": None,
        "flags": {"is_safe_zone": True, "restricted_exits": ["south", "east"]},
        "content": {"title": "Угол Стены", "description": "Тупик.", "environment_tags": ["wall"]},
    },
    # ---------------------------------------------------------
    # ПЕРИМЕТР - ЗАПАД (X=50) и ВОСТОК (X=54)
    # ---------------------------------------------------------
    (50, 51): {
        "sector_id": "D4",
        "is_active": True,
        "service_object_key": None,
        "flags": {"is_safe_zone": True, "restricted_exits": ["west"]},
        "content": {"title": "Западная Стена", "description": "Металлическая стена.", "environment_tags": ["wall"]},
    },
    (50, 52): {
        "sector_id": "D4",
        "is_active": True,
        "service_object_key": None,
        "flags": {"is_safe_zone": False, "is_gate": True},
        "content": {"title": "Западные Ворота", "description": "Выход в пустошь.", "environment_tags": ["gate"]},
    },
    (50, 53): {
        "sector_id": "D4",
        "is_active": True,
        "service_object_key": None,
        "flags": {"is_safe_zone": True, "restricted_exits": ["west"]},
        "content": {"title": "Западная Стена", "description": "Металлическая стена.", "environment_tags": ["wall"]},
    },
    (54, 51): {
        "sector_id": "D4",
        "is_active": True,
        "service_object_key": None,
        "flags": {"is_safe_zone": True, "restricted_exits": ["east"]},
        "content": {"title": "Восточная Стена", "description": "Бетонные блоки.", "environment_tags": ["wall"]},
    },
    (54, 52): {
        "sector_id": "D4",
        "is_active": True,
        "service_object_key": None,
        "flags": {"is_safe_zone": False, "is_gate": True},
        "content": {"title": "Восточные Ворота", "description": "Выход к руинам.", "environment_tags": ["gate"]},
    },
    (54, 53): {
        "sector_id": "D4",
        "is_active": True,
        "service_object_key": None,
        "flags": {"is_safe_zone": True, "restricted_exits": ["east"]},
        "content": {"title": "Восточная Стена", "description": "Бетонные блоки.", "environment_tags": ["wall"]},
    },
    # ==============================================================================
    # 4. ВХОДЫ В ПРАЙМ-РАЗЛОМЫ (На координатах Якорей)
    # ==============================================================================
    (7, 52): {
        "sector_id": "A4",
        "is_active": True,
        "service_object_key": "rift_entry_north_prime",
        "flags": {"is_safe_zone": False, "threat_tier": 7, "is_anchor": True},
        "content": {
            "title": "Разлом 'Зенит'",
            "description": "Эпицентр холода. Радужное сияние застыло в небе. Впереди проход в зону остановленного времени.",
            "environment_tags": ["ice", "stasis", "rift_entry"],
        },
    },
    (97, 52): {
        "sector_id": "G4",
        "is_active": True,
        "service_object_key": "rift_entry_south_prime",
        "flags": {"is_safe_zone": False, "threat_tier": 7, "is_anchor": True},
        "content": {
            "title": "Разлом 'Горнило'",
            "description": "Земля плавится под ногами. Воздух дрожит от жара и радиации. Вход в индустриальный ад.",
            "environment_tags": ["magma", "radiation", "rift_entry"],
        },
    },
    (52, 7): {
        "sector_id": "D1",
        "is_active": True,
        "service_object_key": "rift_entry_west_prime",
        "flags": {"is_safe_zone": False, "threat_tier": 7, "is_anchor": True},
        "content": {
            "title": "Разлом 'Шпиль'",
            "description": "Камни парят в воздухе, игнорируя гравитацию. В центре вихря виден проход в Пустоту.",
            "environment_tags": ["gravity", "void", "rift_entry"],
        },
    },
    (52, 97): {
        "sector_id": "D7",
        "is_active": True,
        "service_object_key": "rift_entry_east_prime",
        "flags": {"is_safe_zone": False, "threat_tier": 7, "is_anchor": True},
        "content": {
            "title": "Разлом 'Сад'",
            "description": "Стены из живой плоти и неона. Воздух сладкий и ядовитый. Вход в сердце Улья.",
            "environment_tags": ["biomass", "poison", "rift_entry"],
        },
    },
}


# ==============================================================================
# 6. БАЗОВЫЕ ТИПЫ ЛОКАЦИЙ (TERRAIN TYPES)
# Используются для заполнения квадратов 5x5.
# ==============================================================================
LOCATION_VARIANTS: dict[str, list[str]] = {
    # Ключ — ID типа, Значение — список базовых тегов
    "dense_forest": ["forest", "trees", "vegetation", "wild"],
    "sparse_forest": ["forest", "clearing", "light_trees"],
    "rocky_hills": ["hills", "rocks", "elevation", "wind"],
    "deep_canyon": ["canyon", "cliffs", "shadows", "echo"],
    "ancient_ruins": ["ruins", "concrete", "old_buildings", "shelter"],
    "flat_wasteland": ["wasteland", "flat", "dust", "open"],
    "swamp": ["swamp", "mud", "water", "reeds"],
}

# Списки для случайного выбора (можно настроить веса/вероятности)
COMMON_LOCATIONS = ["flat_wasteland", "sparse_forest", "rocky_hills", "ancient_ruins"]
RARE_LOCATIONS = ["dense_forest", "deep_canyon", "swamp"]
