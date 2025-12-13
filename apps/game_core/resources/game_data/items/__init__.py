import random
from collections.abc import Mapping
from typing import Any

from .affix_config import BUNDLES_DB
from .bases import BASES_DB

# --- ИМПОРТЫ ДАННЫХ (СКЛАДЫ) ---
from .materials import CRAFTING_MATERIALS_DB
from .rarity_config import get_rarity_by_tier
from .raw_resources import RAW_RESOURCES_DB

# ==========================================
# 1. ГЛОБАЛЬНЫЙ РЕЕСТР (КЭШ)
# ==========================================
# Единый справочник для поиска по ID: { "item_id": { ...данные... } }
ITEM_REGISTRY: dict[str, dict[str, Any]] = {}


def _register_all_items():
    """
    При старте бота пробегает по всем словарям и собирает их в ITEM_REGISTRY.
    """
    # 1. Материалы (rename tiers -> mat_tiers)
    for cat, mat_tiers in CRAFTING_MATERIALS_DB.items():
        for _tier, mat_data in mat_tiers.items():
            _add_to_registry(mat_data, meta_type="material", category=cat)

    # 2. Сырье (rename tiers -> res_tiers)
    for cat, res_tiers in RAW_RESOURCES_DB.items():
        for _tier, res_data in res_tiers.items():
            _add_to_registry(res_data, meta_type="resource", category=cat)

    # 3. Базы (rename items -> base_group)
    for cat, base_group in BASES_DB.items():
        for _item_id, base_data in base_group.items():
            _add_to_registry(base_data, meta_type="base", category=cat)


def _add_to_registry(data: Mapping[str, Any], meta_type: str, category: str):
    """
    Безопасное добавление в реестр.
    Принимает Mapping, чтобы не ругаться на TypedDict.
    """
    item_id = data.get("id")
    if not item_id:
        return  # Пропускаем битые записи

    if item_id in ITEM_REGISTRY:
        print(f"[WARNING] Item Registry duplicate ID detected: {item_id}")
        return

    # Превращаем в обычный dict и копируем
    entry = dict(data)
    entry["_meta_type"] = meta_type
    entry["_meta_category"] = category

    ITEM_REGISTRY[str(item_id)] = entry


# Запускаем индексацию при импорте модуля
_register_all_items()


# ==========================================
# 2. PUBLIC API (ИНТЕРФЕЙСЫ ДЛЯ СЕРВИСОВ)
# ==========================================

# --- A. ИНВЕНТАРЬ И UI ---


def get_item_data(item_id: str) -> dict[str, Any] | None:
    """Возвращает данные предмета (имя, цену, статы) по ID."""
    return ITEM_REGISTRY.get(item_id)


def get_rarity_meta(tier: int) -> Mapping[str, Any]:
    """Возвращает настройки редкости (Цвет, Название) для тира."""
    return get_rarity_by_tier(tier)


# --- B. ГЕНЕРАТОР ЛУТА И КРАФТА ---


def get_material_for_tier(category: str, tier: int) -> Mapping[str, Any] | None:
    """'Дай мне Металл (ingots) 5-го уровня'."""
    return CRAFTING_MATERIALS_DB.get(category, {}).get(tier)


def get_random_base(category_filter: str | None = None) -> dict[str, Any]:
    """'Дай мне случайное оружие'."""
    pool = []

    if category_filter:
        items_map = BASES_DB.get(category_filter)
        if items_map:
            pool = list(items_map.values())
    else:
        for cat_items in BASES_DB.values():
            pool.extend(cat_items.values())

    if not pool:
        raise ValueError(f"CRITICAL: No bases found for category '{category_filter}'")

    # random.choice вернет TypedDict, но для Python это совместимо с Dict
    return dict(random.choice(pool))


def get_base_by_id(base_id: str) -> dict[str, Any] | None:
    """'Игрок хочет скрафтить конкретно Меч (sword)'."""
    item = ITEM_REGISTRY.get(base_id)
    if item and item.get("_meta_type") == "base":
        return item
    return None


# --- C. МАГИЯ И СУФФИКСЫ ---


def get_bundle_by_id(bundle_id: str) -> Mapping[str, Any] | None:
    """Возвращает данные Магического Бандла по его ID."""
    return BUNDLES_DB.get(bundle_id)


def get_bundle_by_ingredient(ingredient_id: str) -> Mapping[str, Any] | None:
    """Обратный поиск: Игрок положил 'Флакон Крови'. Какой бандл он дает?"""
    for bundle in BUNDLES_DB.values():
        if bundle.get("ingredient_id") == ingredient_id:
            return bundle
    return None
