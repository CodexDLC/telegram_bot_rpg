from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, Field


# --- Enums ---
class ItemType(StrEnum):
    WEAPON = "weapon"
    ARMOR = "armor"
    ACCESSORY = "accessory"
    CONSUMABLE = "consumable"
    CONTAINER = "container"
    # 🔥 ДОБАВЛЕНО (было пропущено)
    RESOURCE = "resource"
    CURRENCY = "currency"


class ItemRarity(StrEnum):
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"


# --- Бонусы ---
ItemBonuses = dict[str, float | int]


# --- Базовые данные предмета (Внутри JSON) ---
class ItemCoreData(BaseModel):
    name: str
    description: str
    base_price: int
    weight: float
    material: str
    bonuses: ItemBonuses = Field(default_factory=dict)


# --- Специфика по типам ---


class WeaponData(ItemCoreData):
    damage_min: int
    damage_max: int
    valid_slots: list[str]


class ArmorData(ItemCoreData):
    protection: int
    valid_slots: list[str]
    mobility_penalty: int = 0


class AccessoryData(ItemCoreData):
    valid_slots: list[str]


class ConsumableData(ItemCoreData):
    restore_hp: int = 0
    restore_energy: int = 0
    effects: list[str] = Field(default_factory=list)


class ResourceData(ItemCoreData):
    pass


# --- Полные DTO для API/Кода ---
# 🔥 ВАЖНО: Добавлены поля character_id и location во все классы


class WeaponItemDTO(BaseModel):
    inventory_id: int
    character_id: int  # <--- FIX
    location: str  # <--- FIX
    item_type: Literal[ItemType.WEAPON]
    subtype: str
    rarity: ItemRarity
    data: WeaponData
    quantity: int = 1


class ArmorItemDTO(BaseModel):
    inventory_id: int
    character_id: int  # <--- FIX
    location: str  # <--- FIX
    item_type: Literal[ItemType.ARMOR]
    subtype: str
    rarity: ItemRarity
    data: ArmorData
    quantity: int = 1


class AccessoryItemDTO(BaseModel):
    inventory_id: int
    character_id: int  # <--- FIX
    location: str  # <--- FIX
    item_type: Literal[ItemType.ACCESSORY]
    subtype: str
    rarity: ItemRarity
    data: AccessoryData
    quantity: int = 1


class ConsumableItemDTO(BaseModel):
    inventory_id: int
    character_id: int  # <--- FIX
    location: str  # <--- FIX
    item_type: Literal[ItemType.CONSUMABLE]
    subtype: str
    rarity: ItemRarity
    data: ConsumableData
    quantity: int


class ResourceItemDTO(BaseModel):
    inventory_id: int
    character_id: int  # <--- FIX
    location: str  # <--- FIX
    item_type: Literal[ItemType.RESOURCE, ItemType.CURRENCY]
    subtype: str
    rarity: ItemRarity
    data: ResourceData
    quantity: int


# Полиморфный тип
InventoryItemDTO = Annotated[
    WeaponItemDTO | ArmorItemDTO | AccessoryItemDTO | ConsumableItemDTO | ResourceItemDTO,
    Field(discriminator="item_type"),
]
