"""
ГЛОБАЛЬНЫЙ РЕЕСТР БАЗОВЫХ ПРЕДМЕТОВ
===================================

Этот модуль собирает все категории предметов ("болванок") в единый словарь BASES_DB.

Подробные руководства по заполнению находятся внутри соответствующих модулей:
- Оружие:       apps/game_core/resources/game_data/items/base_item/weapons.py
- Броня:        apps/game_core/resources/game_data/items/base_item/armor.py
- Одежда:       apps/game_core/resources/game_data/items/base_item/garment.py
- Аксессуары:   apps/game_core/resources/game_data/items/base_item/accessories.py
"""

from typing import NotRequired, TypedDict, cast

from .base_item.accessories import ACCESSORIES_DB
from .base_item.armor import ARMOR_DB
from .base_item.garment import GARMENT_DB
from .base_item.weapons import WEAPONS_DB


class BaseItemData(TypedDict):
    id: str
    name_ru: str
    slot: str
    extra_slots: NotRequired[list[str]]
    damage_type: str | None
    defense_type: str | None
    allowed_materials: list[str]
    base_power: int
    base_durability: int
    damage_spread: float
    implicit_bonuses: dict[str, float]
    narrative_tags: list[str]


# Сборка единой базы данных из модулей
BASES_DB: dict[str, dict[str, BaseItemData]] = (
    cast(dict[str, dict[str, BaseItemData]], WEAPONS_DB)
    | cast(dict[str, dict[str, BaseItemData]], ARMOR_DB)
    | cast(dict[str, dict[str, BaseItemData]], GARMENT_DB)
    | cast(dict[str, dict[str, BaseItemData]], ACCESSORIES_DB)
)
