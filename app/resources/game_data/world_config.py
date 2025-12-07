"""
Конфигурация географии мира (Якоря, Хаб, Сектора) и Статических Локаций.
"""

from typing import Any, TypedDict

# ==============================================================================
# 1. ГЛОБАЛЬНАЯ ГЕОМЕТРИЯ
# ==============================================================================
WORLD_WIDTH = 105
WORLD_HEIGHT = 105
SECTOR_SIZE = 15

# Центр Хаба (D4)
HUB_CENTER: dict[str, int] = {"x": 52, "y": 52}

# Маппинг Секторов
SECTOR_ROWS: list[str] = ["A", "B", "C", "D", "E", "F", "G"]


# ==============================================================================
# 2. ЯКОРЯ СТИХИЙ (ANCHORS)
# Источники Поля Угрозы и Нарративных Тегов (ДНК мира).
# ==============================================================================
class _Anchor(TypedDict):
    x: int
    y: int
    power: float
    falloff: float
    type: str
    narrative_tags: list[str]


ANCHORS: list[_Anchor] = [
    # --- СЕВЕР (A4): Лед, Время, Стазис ---
    {
        "x": 7,
        "y": 52,
        "power": 1.2,
        "falloff": 0.08,
        "type": "north_prime",
        "narrative_tags": ["ice", "absolute_zero", "time_stasis", "ancient_tech", "frozen_sky"],
    },
    # --- ЮГ (G4): Огонь, Энтропия, Радиация ---
    {
        "x": 97,
        "y": 52,
        "power": 1.2,
        "falloff": 0.08,
        "type": "south_prime",
        "narrative_tags": ["magma", "ash_clouds", "radiation", "decay", "industrial_ruins"],
    },
    # --- ЗАПАД (D1): Гравитация, Пустота, Шторм ---
    {
        "x": 52,
        "y": 7,
        "power": 1.2,
        "falloff": 0.08,
        "type": "west_prime",
        "narrative_tags": ["zero_gravity", "floating_rocks", "void_storm", "lightning", "shattered_earth"],
    },
    # --- ВОСТОК (D7): Жизнь, Мутация, Кислота ---
    {
        "x": 52,
        "y": 97,
        "power": 1.2,
        "falloff": 0.08,
        "type": "east_prime",
        "narrative_tags": ["neon_biomass", "poison_spores", "giant_roots", "living_flesh", "mutation"],
    },
]

# Параметры Портала (Стабилизатор)
PORTAL_PARAMS: dict[str, float] = {"power": 2.0, "falloff": 0.04}


# ==============================================================================
# 3. STATIC_LOCATIONS: Ручной маппинг активных зон (Хаб "Последний Оплот")
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
