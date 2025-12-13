"""
Модуль содержит DTO (Data Transfer Objects) для работы с игровыми предметами.

Определяет базовые типы предметов, их редкость, а также детальные
структуры данных для различных категорий предметов (оружие, броня,
аксессуары, расходники, ресурсы) и их полиморфное представление.
"""

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


# --- ENUMS ---
class EquippedSlot(StrEnum):
    HEAD_ARMOR = "head_armor"
    CHEST_ARMOR = "chest_armor"
    ARMS_ARMOR = "arms_armor"
    LEGS_ARMOR = "legs_armor"
    FEET_ARMOR = "feet_armor"
    CHEST_GARMENT = "chest_garment"
    LEGS_GARMENT = "legs_garment"
    OUTER_GARMENT = "outer_garment"
    GLOVES_GARMENT = "gloves_garment"
    MAIN_HAND = "main_hand"
    OFF_HAND = "off_hand"
    TWO_HAND = "two_hand"
    AMULET = "amulet"
    EARRING = "earring"
    RING_1 = "ring_1"
    RING_2 = "ring_2"
    BELT_ACCESSORY = "belt_accessory"


class QuickSlot(StrEnum):
    QUICK_SLOT_1 = "quick_slot_1"
    QUICK_SLOT_2 = "quick_slot_2"
    QUICK_SLOT_3 = "quick_slot_3"
    QUICK_SLOT_4 = "quick_slot_4"


class ItemType(StrEnum):
    WEAPON = "weapon"
    ARMOR = "armor"
    ACCESSORY = "accessory"
    CONSUMABLE = "consumable"
    CONTAINER = "container"
    RESOURCE = "resource"
    CURRENCY = "currency"


class ItemRarity(StrEnum):
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"
    MYTHIC = "mythic"
    EXOTIC = "exotic"
    ABSOLUTE = "absolute"


ItemBonuses = dict[str, float | int]


# --- ВСПОМОГАТЕЛЬНЫЕ МОДЕЛИ ---


class ItemComponents(BaseModel):
    """
    Хранит информацию о том, из чего собран предмет.
    """

    base_id: str
    material_id: str
    essence_id: list[str] | None = None  # Теперь это список ID бандлов


class ItemDurability(BaseModel):
    """
    Информация о прочности предмета.
    """

    current: float
    max: float


# --- ОСНОВНЫЕ ДАННЫЕ ---


class ItemCoreData(BaseModel):
    """
    Базовые данные, которые лежат в JSON-поле `item_data` в БД.
    """

    name: str
    description: str
    base_price: int
    components: ItemComponents | None = None
    durability: ItemDurability | None = None
    narrative_tags: list[str] = Field(default_factory=list)
    bonuses: ItemBonuses = Field(default_factory=dict)


# --- СПЕЦИФИЧНЫЕ ДАННЫЕ ---


class WeaponData(ItemCoreData):
    damage_min: int
    damage_max: int
    valid_slots: list[str]


class ArmorData(ItemCoreData):
    protection: int
    valid_slots: list[str]


class AccessoryData(ItemCoreData):
    valid_slots: list[str]


class ConsumableData(ItemCoreData):
    restore_hp: int = 0
    restore_energy: int = 0
    effects: list[str] = Field(default_factory=list)
    cooldown_rounds: int = 0
    is_quick_slot_compatible: bool = False


class ResourceData(ItemCoreData):
    pass


# --- DTO ДЛЯ ИНВЕНТАРЯ ---


class BaseInventoryItemDTO(BaseModel):
    """Основа, маппится на колонки таблицы inventory_items."""

    inventory_id: int
    character_id: int
    location: str
    subtype: str
    rarity: ItemRarity
    quantity: int = 1
    equipped_slot: EquippedSlot | None = None
    quick_slot_position: QuickSlot | None = None
    model_config = ConfigDict(from_attributes=True)


class WeaponItemDTO(BaseInventoryItemDTO):
    item_type: Literal[ItemType.WEAPON]
    data: WeaponData


class ArmorItemDTO(BaseInventoryItemDTO):
    item_type: Literal[ItemType.ARMOR]
    data: ArmorData


class AccessoryItemDTO(BaseInventoryItemDTO):
    item_type: Literal[ItemType.ACCESSORY]
    data: AccessoryData


class ConsumableItemDTO(BaseInventoryItemDTO):
    item_type: Literal[ItemType.CONSUMABLE]
    data: ConsumableData


class ResourceItemDTO(BaseInventoryItemDTO):
    item_type: Literal[ItemType.RESOURCE, ItemType.CURRENCY]
    data: ResourceData


# Полиморфный Union
InventoryItemDTO = Annotated[
    WeaponItemDTO | ArmorItemDTO | AccessoryItemDTO | ConsumableItemDTO | ResourceItemDTO,
    Field(discriminator="item_type"),
]
