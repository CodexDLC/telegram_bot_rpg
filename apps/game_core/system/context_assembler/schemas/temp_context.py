from typing import Any

from pydantic import BaseModel, computed_field

# Импортируем Enums для логики
from apps.common.enums.stats_enum import PrimaryStat

# Импортируем твои существующие DTO (Core Data)
from apps.common.schemas_dto.character_dto import CharacterReadDTO, CharacterStatsReadDTO
from apps.common.schemas_dto.skill import SkillProgressDTO
from apps.game_core.system.context_assembler.utils import format_value


class TempContextSchema(BaseModel):
    """
    MASTER SCHEMA for Redis Temp Context.
    Содержит полные сырые данные + готовые проекции для систем.
    """

    # --- 1. CORE DATA (Источник правды) ---
    # Храним полные объекты, чтобы любой сервис мог получить доступ к деталям
    core_stats: CharacterStatsReadDTO
    core_inventory: list[Any]  # InventoryItemDTO или dict
    core_skills: list[SkillProgressDTO]
    core_vitals: dict[str, Any]  # {"hp": {"cur": 100}, ...}
    core_meta: CharacterReadDTO
    core_symbiote: dict[str, Any] | None = None  # Сериализованный симбиот

    # --- 2. COMPUTED VIEWS (Готовые проекции) ---

    @computed_field(alias="math_model")
    def combat_view(self) -> dict[str, Any]:
        """
        Проекция для COMBAT SERVICE (RBC Protocol).
        Автоматически собирает v:raw матрицу.
        """
        model: dict[str, Any] = {
            "attributes": {},
            "modifiers": {},
            "tags": ["player", "human"],  # TODO: Race tag
        }

        # 1. Attributes Base
        stats_dict = self.core_stats.model_dump()
        for stat_enum in PrimaryStat:
            key = stat_enum.value
            val = stats_dict.get(key, 0)
            model["attributes"][key] = {"base": str(float(val)), "flats": {}, "percents": {}}

        # 2. Equipment Bonuses
        for item in self.core_inventory:
            # Обработка Pydantic модели или dict
            item_data = item.model_dump() if hasattr(item, "model_dump") else item

            loc = item_data.get("location")
            if loc == "equipped" and item_data.get("data") and item_data["data"].get("bonuses"):
                for stat, val in item_data["data"]["bonuses"].items():
                    src = f"item:{item_data.get('item_id')}"
                    val_str = format_value(stat, val, "external")

                    # Распределяем по attributes/modifiers
                    if stat in model["attributes"]:
                        model["attributes"][stat]["flats"][src] = val_str
                    else:
                        if stat not in model["modifiers"]:
                            model["modifiers"][stat] = {"sources": {}}
                        model["modifiers"][stat]["sources"][src] = val_str

            # Обработка базового урона оружия и брони
            if loc == "equipped":
                item_type = item_data.get("item_type")
                src = f"item:{item_data.get('item_id')}"

                if item_type == "weapon":
                    dmg_min = item_data["data"].get("damage_min")
                    dmg_max = item_data["data"].get("damage_max")
                    if dmg_min:
                        if "physical_damage_min" not in model["modifiers"]:
                            model["modifiers"]["physical_damage_min"] = {"sources": {}}
                        model["modifiers"]["physical_damage_min"]["sources"][src] = format_value(
                            "physical_damage_min", dmg_min, "external"
                        )
                    if dmg_max:
                        if "physical_damage_max" not in model["modifiers"]:
                            model["modifiers"]["physical_damage_max"] = {"sources": {}}
                        model["modifiers"]["physical_damage_max"]["sources"][src] = format_value(
                            "physical_damage_max", dmg_max, "external"
                        )

                if item_type == "armor":
                    prot = item_data["data"].get("protection")
                    if prot:
                        # Упрощенно: все в damage_reduction_flat
                        if "damage_reduction_flat" not in model["modifiers"]:
                            model["modifiers"]["damage_reduction_flat"] = {"sources": {}}
                        model["modifiers"]["damage_reduction_flat"]["sources"][src] = format_value(
                            "damage_reduction_flat", prot, "external"
                        )

        return model

    @computed_field(alias="loadout")
    def loadout_view(self) -> dict[str, Any]:
        """
        Проекция для UI/Inventory Service.
        """
        belt = []
        for item in self.core_inventory:
            item_data = item.model_dump() if hasattr(item, "model_dump") else item
            if item_data.get("quick_slot_position"):
                belt.append(item_data)

        return {
            "belt": belt,
            "skills": [s.skill_key for s in self.core_skills if s.is_unlocked],
            "abilities": [],  # Заглушка
        }

    @computed_field(alias="vitals")
    def vitals_view(self) -> dict[str, Any]:
        hp = 100
        en = 100
        if self.core_vitals:
            hp = self.core_vitals.get("hp", {}).get("cur", 100)
            en = self.core_vitals.get("energy", {}).get("cur", 100)
        return {"hp_current": hp, "energy_current": en}

    @computed_field(alias="meta")
    def meta_view(self) -> dict[str, Any]:
        """
        Общая мета-информация.
        """
        return {
            "entity_id": self.core_meta.character_id,
            "type": "player",
            "timestamp": 0,
            "character": {
                "name": self.core_meta.name,
                "gender": self.core_meta.gender,
                "game_stage": self.core_meta.game_stage,
                "prev_game_stage": self.core_meta.prev_game_stage,
                "location_id": self.core_meta.location_id,
                "prev_location_id": self.core_meta.prev_location_id,
            },
            "symbiote": self.core_symbiote,
        }
