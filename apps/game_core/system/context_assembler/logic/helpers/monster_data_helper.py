# apps/game_core/system/context_assembler/logic/helpers/monster_data_helper.py
from typing import Any

from loguru import logger as log

from apps.game_core.resources.game_data.items.bases import BASES_DB
from apps.game_core.resources.game_data.monsters.monster_equipment import MONSTER_EQUIPMENT_DB
from apps.game_core.system.context_assembler.utils import format_value


def get_equipment_modifiers(loadout: dict | Any) -> dict[str, dict[str, str]]:
    """
    Собирает модификаторы от экипировки монстра.
    Ищет предметы в BASES_DB и MONSTER_EQUIPMENT_DB.

    Returns:
        Словарь модификаторов, готовый для вставки в v:raw.
        Пример: {"physical_damage_min": {"sources": {"item:claws": "+5"}}}
    """
    if not loadout:
        return {}

    loadout_dict = loadout
    if hasattr(loadout, "model_dump"):
        loadout_dict = loadout.model_dump(exclude_none=True)

    if not isinstance(loadout_dict, dict):
        return {}

    all_modifiers: dict[str, dict[str, Any]] = {}

    for _slot, item_key in loadout_dict.items():
        if not item_key:
            continue

        item_data = None
        item_category = None

        for category, items in BASES_DB.items():
            if item_key in items:
                item_data = items[item_key]
                item_category = category
                break

        if not item_data:
            item_data = MONSTER_EQUIPMENT_DB.get(item_key)
            if item_data:
                item_category = "monster_equipment"

        if not item_data:
            log.warning(f"MonsterDataHelper | Item '{item_key}' not found in DBs")
            continue

        # 1. Врожденные бонусы (External)
        bonuses = item_data.get("implicit_bonuses", {})
        for stat, val in bonuses.items():
            if stat not in all_modifiers:
                all_modifiers[stat] = {"sources": {}}
            # Используем source_type="external" для правильного форматирования (* или +)
            all_modifiers[stat]["sources"][f"item:{item_key}"] = format_value(stat, val, source_type="external")

        # 2. Специфичные статы (Урон, Броня) - Тоже External, но format_value знает, что это "+"
        base_power = float(item_data.get("base_power", 0))
        item_type = item_data.get("type")

        if not item_type:
            if item_category in ["light_1h", "medium_1h", "melee_2h", "ranged", "shields"]:
                item_type = "weapon"
            elif item_category in ["heavy_armor", "medium_armor", "light_armor", "garment", "accessories"]:
                item_type = "armor"

        if item_type == "weapon":
            spread = float(item_data.get("damage_spread", 0.1))
            dmg_min = base_power * (1.0 - spread)
            dmg_max = base_power * (1.0 + spread)

            if "physical_damage_min" not in all_modifiers:
                all_modifiers["physical_damage_min"] = {"sources": {}}
            all_modifiers["physical_damage_min"]["sources"][f"item:{item_key}"] = format_value(
                "physical_damage_min", dmg_min, "external"
            )

            if "physical_damage_max" not in all_modifiers:
                all_modifiers["physical_damage_max"] = {"sources": {}}
            all_modifiers["physical_damage_max"]["sources"][f"item:{item_key}"] = format_value(
                "physical_damage_max", dmg_max, "external"
            )

        elif item_type == "armor":
            if "damage_reduction_flat" not in all_modifiers:
                all_modifiers["damage_reduction_flat"] = {"sources": {}}
            all_modifiers["damage_reduction_flat"]["sources"][f"item:{item_key}"] = format_value(
                "damage_reduction_flat", base_power, "external"
            )

    # Cast to expected return type
    return all_modifiers  # type: ignore
