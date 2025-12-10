"""
Модуль содержит полную библиотеку всех игровых ресурсов.

Каждый ресурс описывается словарем `ResourceData`, включающим
название, тип, подтип, уровень редкости (tier), вес, базовую цену
и описание.
"""

from typing import TypedDict


class ResourceData(TypedDict):
    name: str
    type: str
    subtype: str | None
    tier: int
    weight: float
    base_price: int
    description: str


RESOURCE_LIBRARY: dict[str, ResourceData] = {
    "residuum_dust": {
        "name": "Пыль Резидуу",
        "type": "currency",
        "subtype": "dust",
        "tier": 1,
        "weight": 0.001,
        "base_price": 1,
        "description": "Мерцающий песок. Остаточная энергия Рифтов. Основа экономики и магии.",
    },
    "residuum_shard": {
        "name": "Стабильный Осколок",
        "type": "currency",
        "subtype": "shard",
        "tier": 2,
        "weight": 0.1,
        "base_price": 1000,
        "description": "Спрессованная энергия. Принимается торговцами как вексель.",
    },
    "residuum_core": {
        "name": "Ядро Чистоты",
        "type": "currency",
        "subtype": "core",
        "tier": 3,
        "weight": 0.5,
        "base_price": 100000,
        "description": "Идеальная форма энергии. Целое состояние в одном камне.",
    },
    "scrap_metal": {
        "name": "Ржавый лом",
        "type": "metal",
        "subtype": "scrap",
        "tier": 1,
        "weight": 0.5,
        "base_price": 1,
        "description": "Куски старого металла, изъеденные коррозией.",
    },
    "iron_ingot": {
        "name": "Железный слиток",
        "type": "metal",
        "subtype": "ingot",
        "tier": 2,
        "weight": 1.0,
        "base_price": 5,
        "description": "Добротный кусок железа. Стандарт для кузнецов.",
    },
    "steel_alloy": {
        "name": "Закаленная сталь",
        "type": "metal",
        "subtype": "alloy",
        "tier": 3,
        "weight": 0.8,
        "base_price": 25,
        "description": "Прочный сплав. Блестит на свету.",
    },
    "titanium_ore": {
        "name": "Титановая руда",
        "type": "metal",
        "subtype": "ore",
        "tier": 4,
        "weight": 1.2,
        "base_price": 100,
        "description": "Легкий и прочный металл древних времен.",
    },
    "torn_hide": {
        "name": "Рваная шкура",
        "type": "leather",
        "subtype": "hide",
        "tier": 1,
        "weight": 0.3,
        "base_price": 1,
        "description": "Шкура плохого качества, вся в дырах.",
    },
    "cured_leather": {
        "name": "Дубленая кожа",
        "type": "leather",
        "subtype": "leather",
        "tier": 2,
        "weight": 0.5,
        "base_price": 4,
        "description": "Обработанная жесткая кожа.",
    },
    "beast_scale": {
        "name": "Чешуя зверя",
        "type": "leather",
        "subtype": "scale",
        "tier": 3,
        "weight": 0.4,
        "base_price": 20,
        "description": "Твердая роговая пластина опасного хищника.",
    },
    "chimera_skin": {
        "name": "Шкура Химеры",
        "type": "leather",
        "subtype": "skin",
        "tier": 4,
        "weight": 0.6,
        "base_price": 90,
        "description": "Переливающаяся шкура магического существа.",
    },
    "dirty_rags": {
        "name": "Грязные тряпки",
        "type": "cloth",
        "subtype": "rag",
        "tier": 1,
        "weight": 0.1,
        "base_price": 1,
        "description": "Ветошь со свалки.",
    },
    "linen_roll": {
        "name": "Льняной рулон",
        "type": "cloth",
        "subtype": "roll",
        "tier": 2,
        "weight": 0.2,
        "base_price": 3,
        "description": "Простая, но чистая ткань.",
    },
    "silk_weave": {
        "name": "Шелковое плетение",
        "type": "cloth",
        "subtype": "weave",
        "tier": 3,
        "weight": 0.1,
        "base_price": 15,
        "description": "Тонкая ткань, проводящая ману.",
    },
    "moon_fiber": {
        "name": "Лунное волокно",
        "type": "cloth",
        "subtype": "fiber",
        "tier": 4,
        "weight": 0.05,
        "base_price": 80,
        "description": "Светится в темноте. Нити из чистого света.",
    },
}
