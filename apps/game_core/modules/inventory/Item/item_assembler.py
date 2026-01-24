import random
from typing import Any, cast

from loguru import logger as log

from apps.common.schemas_dto.item_dto import ItemType
from backend.resources.game_data.items import (
    get_base_by_id,
    get_material_for_tier,
    get_rarity_meta,
)
from backend.resources.game_data.items import (
    BUNDLES_DB,
    EFFECTS_DB,
    BundleData,
)
from backend.resources.game_data.items.bases import BaseItemData
from backend.resources.game_data.items import MaterialStats


class ItemAssembler:
    """
    Фабрика для сборки игровых предметов (Equipment).
    Превращает набор ID (base, material, bundle) в готовый словарь данных (JSON payload).
    """

    @staticmethod
    def assemble_equipment(
        base_id: str,
        target_tier: int,
        bundle_id: str | None = None,
    ) -> tuple[str, str, str, dict[str, Any]]:
        """
        Создает экипировку (Оружие, Броня, Аксессуары).
        """
        raw_base_data = get_base_by_id(base_id)
        if not raw_base_data:
            raise ValueError(f"Base item not found: {base_id}")
        base_data = cast(BaseItemData, raw_base_data)

        material_cat = base_data["allowed_materials"][0]
        raw_material_data = get_material_for_tier(material_cat, target_tier)
        if not raw_material_data:
            log.warning(f"Material tier {target_tier} for {material_cat} not found. Fallback to 0.")
            raw_material_data = get_material_for_tier(material_cat, 0)
            target_tier = 0

        if not raw_material_data:
            raise ValueError(f"Critical: No material found for category {material_cat}")

        material_data = cast(MaterialStats, raw_material_data)

        rarity_meta = get_rarity_meta(target_tier)
        rarity_enum = rarity_meta["enum_key"]

        mult = material_data["tier_mult"]
        variance = random.uniform(0.9, 1.1)
        final_mult = mult * variance

        final_power = int(base_data["base_power"] * final_mult)
        max_durability = int(base_data["base_durability"] * mult)

        item_type = ItemAssembler._get_item_type_from_slot(base_data["slot"])
        item_name = f"{material_data['name_ru']} {base_data['name_ru'].split()[-1]}"

        final_bonuses = base_data.get("implicit_bonuses", {}).copy()

        if base_id == "belt":
            base_slots = final_bonuses.get("quick_slot_capacity", 1.0)
            material_slots = material_data.get("slots", 0)
            total_slots = base_slots + material_slots
            final_bonuses["quick_slot_capacity"] = float(total_slots)

        valid_slots = [base_data["slot"]]
        if "extra_slots" in base_data:
            valid_slots.extend(base_data["extra_slots"])  # type: ignore

        data_payload = {
            "name": item_name,
            "description": f"Создано из {material_data['name_ru']}.",
            "base_price": int(10 * final_mult * (target_tier + 1)),
            "narrative_tags": base_data["narrative_tags"] + material_data["narrative_tags"],
            "components": {"base_id": base_id, "material_id": material_data["id"]},
            "durability": {"current": max_durability, "max": max_durability},
            "valid_slots": valid_slots,
            "bonuses": final_bonuses,
        }

        if item_type == ItemType.WEAPON:
            spread = base_data.get("damage_spread", 0.2)
            dmg_min = int(final_power * (1 - spread))
            dmg_max = int(final_power * (1 + spread))
            data_payload["damage_min"] = max(1, dmg_min)
            data_payload["damage_max"] = max(2, dmg_max)
        elif item_type == ItemType.ARMOR or item_type == ItemType.ACCESSORY:
            data_payload["protection"] = max(1, final_power)

        ItemAssembler._apply_bundles(data_payload, material_data, bundle_id)

        return item_type, base_id, rarity_enum, data_payload

    @staticmethod
    def _apply_bundles(
        data_payload: dict[str, Any],
        material_data: MaterialStats,
        primary_bundle_id: str | None,
    ):
        available_slots = material_data.get("slots", 0)
        if available_slots <= 0:
            return

        bundles_to_apply: list[BundleData] = []
        remaining_slots = available_slots

        if primary_bundle_id:
            bundle = BUNDLES_DB.get(primary_bundle_id)
            if bundle and bundle["cost_slots"] <= remaining_slots:
                bundles_to_apply.append(bundle)
                remaining_slots -= bundle["cost_slots"]
            else:
                log.warning(f"Primary bundle {primary_bundle_id} skipped (cost/exist check failed).")

        while remaining_slots > 0:
            possible_candidates = [b for b in BUNDLES_DB.values() if b["cost_slots"] <= remaining_slots]
            if not possible_candidates:
                break

            chosen_bundle = random.choice(possible_candidates)
            bundles_to_apply.append(chosen_bundle)
            remaining_slots -= chosen_bundle["cost_slots"]

        if not bundles_to_apply:
            return

        all_bundle_ids = []
        for bundle in bundles_to_apply:
            all_bundle_ids.append(bundle["id"])
            data_payload["narrative_tags"].extend(bundle["narrative_tags"])

            for effect_key in bundle["effects"]:
                effect = EFFECTS_DB.get(effect_key)
                if not effect:
                    continue

                final_value = effect["base_value"] * material_data["tier_mult"]
                target_field = effect["target_field"]

                current_bonus = data_payload["bonuses"].get(target_field, 0.0)
                data_payload["bonuses"][target_field] = current_bonus + final_value

        data_payload["components"]["essence_id"] = all_bundle_ids
        suffix = " ".join([f"<{b['id'].capitalize()}>" for b in bundles_to_apply])
        data_payload["name"] += f" {suffix}"

    @staticmethod
    def _get_item_type_from_slot(slot: str) -> ItemType:
        if slot in ["main_hand", "off_hand", "two_hand"]:
            return ItemType.WEAPON
        if slot in ["amulet", "ring_1", "ring_2", "earring", "belt_accessory"]:
            return ItemType.ACCESSORY
        return ItemType.ARMOR
