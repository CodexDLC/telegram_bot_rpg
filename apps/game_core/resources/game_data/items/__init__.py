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
ITEM_REGISTRY: dict[str, dict[str, Any]] = {}
_INGREDIENT_TO_BUNDLE_MAP: dict[str, Mapping[str, Any]] = {}


def _build_reverse_maps():
    """Строит обратные индексы для быстрого поиска."""
    for bundle in BUNDLES_DB.values():
        if ingredient_id := bundle.get("ingredient_id"):
            if ingredient_id in _INGREDIENT_TO_BUNDLE_MAP:
                print(f"[WARNING] Duplicate ingredient_id in bundles: {ingredient_id}")
            _INGREDIENT_TO_BUNDLE_MAP[ingredient_id] = bundle


def _register_all_items():
    """
    При старте бота пробегает по всем словарям и собирает их в ITEM_REGISTRY.
    """
    # 1. Материалы
    for cat, mat_tiers in CRAFTING_MATERIALS_DB.items():
        for _tier, mat_data in mat_tiers.items():
            _add_to_registry(mat_data, meta_type="material", category=cat)

    # 2. Сырье
    for cat, res_data in RAW_RESOURCES_DB.items():
        if cat == "supplies":
            for _id, data in res_data.items():
                _add_to_registry(data, meta_type="resource", category=cat)
        else:
            for _tier, data in res_data.items():
                _add_to_registry(data, meta_type="resource", category=cat)

    # 3. Базы
    for cat, base_group in BASES_DB.items():
        for _item_id, base_data in base_group.items():
            _add_to_registry(base_data, meta_type="base", category=cat)

    # 4. Строим обратные карты
    _build_reverse_maps()


def _add_to_registry(data: Mapping[str, Any], meta_type: str, category: str):
    """
    Безопасное добавление в реестр.
    """
    item_id = data.get("id")
    if not item_id:
        return

    if item_id in ITEM_REGISTRY:
        print(f"[WARNING] Item Registry duplicate ID detected: {item_id}")
        return

    entry = dict(data)
    entry["_meta_type"] = meta_type
    entry["_meta_category"] = category
    ITEM_REGISTRY[str(item_id)] = entry


# Запускаем индексацию при импорте модуля
_register_all_items()


# ==========================================
# 2. PUBLIC API (ИНТЕРФЕЙСЫ ДЛЯ СЕРВИСОВ)
# ==========================================

# --- A. ОБЩИЕ ---


def get_item_data(item_id: str) -> dict[str, Any] | None:
    """Возвращает данные предмета (имя, цену, статы) по ID."""
    return ITEM_REGISTRY.get(item_id)


# --- B. ГЕНЕРАТОР ЛУТА И UI ---


def get_rarity_meta(tier: int) -> Mapping[str, Any]:
    """Возвращает настройки редкости (Цвет, Название) для тира."""
    return get_rarity_by_tier(tier)


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
    return dict(random.choice(pool))


# --- C. КРАФТ И РЕЦЕПТЫ (валидаторы) ---


def get_base_by_id(base_id: str) -> dict[str, Any] | None:
    """'Игрок хочет скрафтить конкретно Меч (sword)'."""
    item = ITEM_REGISTRY.get(base_id)
    if item and item.get("_meta_type") == "base":
        return item
    return None


def get_material_for_tier(category: str, tier: int) -> Mapping[str, Any] | None:
    """'Дай мне Металл (ingots) 5-го уровня'."""
    return CRAFTING_MATERIALS_DB.get(category, {}).get(tier)


def is_material(item_id: str) -> bool:
    """Проверяет, является ли ID материалом для крафта."""
    item = ITEM_REGISTRY.get(item_id)
    return item is not None and item.get("_meta_type") == "material"


def is_resource(item_id: str) -> bool:
    """Проверяет, является ли ID сырьевым ресурсом (не 'supplies')."""
    item = ITEM_REGISTRY.get(item_id)
    return item is not None and item.get("_meta_type") == "resource" and item.get("_meta_category") != "supplies"


def is_supply(item_id: str) -> bool:
    """Проверяет, является ли ID ремесленным расходником."""
    item = ITEM_REGISTRY.get(item_id)
    return item is not None and item.get("_meta_type") == "resource" and item.get("_meta_category") == "supplies"


# --- D. МАГИЯ И СУФФИКСЫ ---


def get_bundle_by_id(bundle_id: str) -> Mapping[str, Any] | None:
    """Возвращает данные Магического Бандла по его ID."""
    return BUNDLES_DB.get(bundle_id)


def get_bundle_by_ingredient(ingredient_id: str) -> Mapping[str, Any] | None:
    """Обратный поиск O(1) с использованием предварительно созданного индекса."""
    return _INGREDIENT_TO_BUNDLE_MAP.get(ingredient_id)


# --- E. COMBAT HELPERS ---


def get_weapon_trigger(base_id: str) -> str | None:
    """
    Возвращает ID триггера атаки для базового оружия.
    Берет первый элемент из списка triggers.
    """
    item = ITEM_REGISTRY.get(base_id)
    if not item:
        return None

    # Проверяем, что это оружие (опционально, но полезно)
    # if item.get("type") != "weapon":
    #     return None

    triggers = item.get("triggers")
    if triggers and isinstance(triggers, list) and len(triggers) > 0:
        return triggers[0]

    return None
