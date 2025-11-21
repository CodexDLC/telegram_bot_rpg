from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, Field


# --- Enums ---
class ItemType(StrEnum):
    WEAPON = "weapon"
    ARMOR = "armor"
    ACCESSORY = "accessory"
    CONSUMABLE = "consumable"


class ItemRarity(StrEnum):
    COMMON = "common"  # 0 бонусов
    UNCOMMON = "uncommon"  # 1-2 бонуса
    RARE = "rare"  # 2-3 бонуса
    EPIC = "epic"  # 3-4 бонуса + усиленные статы
    LEGENDARY = "legendary"  # 4+ бонусов + уникальная механика


# --- Бонусы ---
ItemBonuses = dict[str, float | int]


# --- Базовые данные предмета (Внутри JSON) ---
class ItemCoreData(BaseModel):
    name: str  # Генерируется ИИ (напр. "Пожиратель Душ")
    description: str  # Генерируется ИИ
    base_price: int  # Расчитывается формулой от рарности
    weight: float

    # Бонусы (те самые аффиксы, которые наролил генератор)
    bonuses: ItemBonuses = Field(default_factory=dict)


# --- Специфика по типам ---


class WeaponData(ItemCoreData):
    damage_min: int
    damage_max: int
    # Какие слоты занимает (Main Hand, Two Hand...)
    valid_slots: list[str]


class ArmorData(ItemCoreData):
    protection: int
    # Куда надевается (Head, Chest...)
    valid_slots: list[str]
    mobility_penalty: int = 0


class AccessoryData(ItemCoreData):
    # Куда надевается (Finger, Neck...)
    valid_slots: list[str]


class ConsumableData(ItemCoreData):
    restore_hp: int = 0
    restore_energy: int = 0
    effects: list[str] = Field(default_factory=list)


# --- Полные DTO для API/Кода ---
# Мы используем их, чтобы читать JSON из базы и работать с ним как с объектами


class WeaponItemDTO(BaseModel):
    inventory_id: int
    item_type: Literal[ItemType.WEAPON]
    subtype: str
    rarity: ItemRarity
    data: WeaponData  # <-- Вся инфа тут


class ArmorItemDTO(BaseModel):
    inventory_id: int
    item_type: Literal[ItemType.ARMOR]
    subtype: str
    rarity: ItemRarity
    data: ArmorData


class AccessoryItemDTO(BaseModel):
    inventory_id: int
    item_type: Literal[ItemType.ACCESSORY]
    subtype: str
    rarity: ItemRarity
    data: AccessoryData


class ConsumableItemDTO(BaseModel):
    inventory_id: int
    item_type: Literal[ItemType.CONSUMABLE]
    subtype: str
    rarity: ItemRarity
    data: ConsumableData


# Полиморфный тип
InventoryItemDTO = Annotated[
    WeaponItemDTO | ArmorItemDTO | AccessoryItemDTO | ConsumableItemDTO, Field(discriminator="item_type")
]
