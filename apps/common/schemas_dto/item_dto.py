from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


# --- ENUMS (Остаются без изменений) ---
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
    MYTHIC = "mythic"  # Добавлено согласно новой концепции
    EXOTIC = "exotic"  # Добавлено согласно новой концепции
    ABSOLUTE = "absolute"  # Добавлено согласно новой концепции


ItemBonuses = dict[str, float | int]


# --- НОВЫЕ ВСПОМОГАТЕЛЬНЫЕ МОДЕЛИ ---


class ItemComponents(BaseModel):
    """
    Хранит информацию о том, из чего собран предмет.
    Нужно для механики разбора (Dismantle) и ре-ролла.
    """

    base_id: str  # ID базы (например, 'sword')
    material_id: str  # ID материала (например, 'mat_void_ingot')
    essence_id: str | None = None  # ID эссенции/бандла (например, 'bundle_vampire')


class ItemDurability(BaseModel):
    """
    Информация о прочности предмета.
    """

    current: float  # Текущая прочность (может быть дробной из-за формул износа)
    max: float  # Максимальная прочность (зависит от Материала)


# --- ОБНОВЛЕННАЯ СТРУКТУРА ДАННЫХ (CORE) ---


class ItemCoreData(BaseModel):
    """
    Базовые данные, которые лежат в JSON-поле `item_data` в БД.
    """

    name: str  # Сгенерированное имя ("Меч Кровавой Луны")
    description: str  # Сгенерированное описание
    base_price: int  # Цена продажи

    # --- Новые поля для Генератора ---
    components: ItemComponents | None = None  # Состав предмета
    durability: ItemDurability | None = None  # Прочность (None для ресурсов)
    narrative_tags: list[str] = Field(default_factory=list)  # Теги для LLM и UI

    # --- Старые поля (для совместимости) ---
    material: str = "unknown"  # Оставляем строкой для совместимости, но логика теперь в components
    bonuses: ItemBonuses = Field(default_factory=dict)


# --- СПЕЦИФИЧНЫЕ ДАННЫЕ (Почти без изменений, наследуют новые поля) ---


class WeaponData(ItemCoreData):
    damage_min: int
    damage_max: int
    # damage_type: str = "physical" # Можно добавить, если нужно в UI
    valid_slots: list[str]


class ArmorData(ItemCoreData):
    protection: int
    mobility_penalty: int = 0
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
    """Ресурсы обычно не имеют прочности и компонентов."""

    pass


# --- DTO ДЛЯ ИНВЕНТАРЯ (Обертки) ---


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
