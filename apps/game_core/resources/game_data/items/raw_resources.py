"""
ГЛОБАЛЬНЫЙ РЕЕСТР СЫРЬЕВЫХ РЕСУРСОВ
====================================

Этот модуль собирает все категории сырья в единый словарь RAW_RESOURCES_DB.

Подробные данные находятся внутри соответствующих модулей в папке `raw_resource/`.
"""

from typing import Any, TypedDict, cast

from .raw_resource.bark import BARK_DB
from .raw_resource.common_supplies import COMMON_SUPPLIES_DB
from .raw_resource.currency import CURRENCY_DB
from .raw_resource.essences import ESSENCES_DB
from .raw_resource.fibers import FIBERS_DB
from .raw_resource.flowers import FLOWERS_DB
from .raw_resource.hides import HIDES_DB
from .raw_resource.ores import ORES_DB
from .raw_resource.stone import STONE_DB
from .raw_resource.woods import WOODS_DB


class ResourceData(TypedDict):
    id: str
    name_ru: str
    base_price: int
    narrative_description: str


# Сборка единой базы данных из модулей
# Используем оператор | (Python 3.9+) для объединения словарей
RAW_RESOURCES_DB: dict[str, dict[Any, ResourceData]] = (
    cast(dict[str, dict[Any, ResourceData]], CURRENCY_DB)
    | cast(dict[str, dict[Any, ResourceData]], ORES_DB)
    | cast(dict[str, dict[Any, ResourceData]], HIDES_DB)
    | cast(dict[str, dict[Any, ResourceData]], WOODS_DB)
    | cast(dict[str, dict[Any, ResourceData]], FIBERS_DB)
    | cast(dict[str, dict[Any, ResourceData]], ESSENCES_DB)
    | cast(dict[str, dict[Any, ResourceData]], STONE_DB)
    | cast(dict[str, dict[Any, ResourceData]], BARK_DB)
    | cast(dict[str, dict[Any, ResourceData]], FLOWERS_DB)
    | cast(dict[str, dict[Any, ResourceData]], COMMON_SUPPLIES_DB)
)
