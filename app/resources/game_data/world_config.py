"""
Конфигурация географии мира: Якоря, Палитры биомов и Статика.
Источники данных для генерации тегов.
"""

from typing import TypedDict

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
    # Север (Ле-д) + Восток (Био) = Крио-Сон / Сохранение
    frozenset(["ice", "bio"]): ["preserved_corpses", "frozen_flowers", "hibernate"],
    # Юг (Огонь) + Запад (Гравитация) = Плазменный Шторм
    frozenset(["fire", "gravity"]): ["plasma_arcs", "flying_lava", "solar_flare"],
    # Юг (Огонь) + Восток (Био) = Гниение / Болото (Тепло + Влага)
    frozenset(["fire", "bio"]): ["boiling_swamp", "rotting_flesh", "steam", "disease"],
}


# ==============================================================================
# 5. БАЗОВЫЕ ТИПЫ ЛОКАЦИЙ (TERRAIN TYPES)
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
