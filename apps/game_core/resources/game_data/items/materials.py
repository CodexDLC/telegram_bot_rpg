"""
ГЛОБАЛЬНЫЙ РЕЕСТР МАТЕРИАЛОВ
============================

Этот модуль собирает все категории обработанных материалов и деталей в единый словарь CRAFTING_MATERIALS_DB.

Подробные данные находятся внутри соответствующих модулей в папке `material/`.
"""

from typing import TypedDict, cast

from .material.cloths import CLOTHS_DB
from .material.ingots import INGOTS_DB
from .material.leathers import LEATHERS_DB
from .material.parts import PARTS_DB
from .material.woods import WOODS_DB


class MaterialStats(TypedDict):
    id: str
    name_ru: str
    tier_mult: float
    slots: int
    narrative_tags: list[str]


# Сборка единой базы данных из модулей
CRAFTING_MATERIALS_DB: dict[str, dict[int, MaterialStats]] = (
    cast(dict[str, dict[int, MaterialStats]], INGOTS_DB)
    | cast(dict[str, dict[int, MaterialStats]], LEATHERS_DB)
    | cast(dict[str, dict[int, MaterialStats]], CLOTHS_DB)
    | cast(dict[str, dict[int, MaterialStats]], WOODS_DB)
    | cast(dict[str, dict[int, MaterialStats]], PARTS_DB)
)
