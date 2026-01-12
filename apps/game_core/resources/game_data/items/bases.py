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

from typing import cast

from apps.game_core.resources.game_data.items.schemas import BaseItemDTO

from .base_item.accessories import ACCESSORIES_DB
from .base_item.armor import ARMOR_DB
from .base_item.garment import GARMENT_DB
from .base_item.weapons import WEAPONS_DB

# Сборка единой базы данных из модулей
BASES_DB: dict[str, dict[str, BaseItemDTO]] = (
    cast(dict[str, dict[str, BaseItemDTO]], WEAPONS_DB)
    | cast(dict[str, dict[str, BaseItemDTO]], ARMOR_DB)
    | cast(dict[str, dict[str, BaseItemDTO]], GARMENT_DB)
    | cast(dict[str, dict[str, BaseItemDTO]], ACCESSORIES_DB)
)
