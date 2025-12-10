"""
Модуль содержит DTO (Data Transfer Objects) для работы с игровыми предметами.

Определяет базовые типы предметов, их редкость, а также детальные
структуры данных для различных категорий предметов (оружие, броня,
аксессуары, расходники, ресурсы) и их полиморфное представление.
"""

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class EquippedSlot(StrEnum):
    """Перечисление всех конкретных слотов для экипировки (Кукла)."""

    # Броня (Armor)
    HEAD_ARMOR = "head_armor"
    CHEST_ARMOR = "chest_armor"
    ARMS_ARMOR = "arms_armor"
    LEGS_ARMOR = "legs_armor"
    FEET_ARMOR = "feet_armor"

    # Одежда (Garment)
    CHEST_GARMENT = "chest_garment"
    LEGS_GARMENT = "legs_garment"
    OUTER_GARMENT = "outer_garment"
    GLOVES_GARMENT = "gloves_garment"

    # 👇 НЕДОСТАЮЩИЕ СЛОТЫ ОРУЖИЯ (Мы добавили их)
    MAIN_HAND = "main_hand"
    OFF_HAND = "off_hand"
    TWO_HAND = "two_hand"

    # Аксессуары
    AMULET = "amulet"
    EARRING = "earring"
    RING_1 = "ring_1"
    RING_2 = "ring_2"
    BELT_ACCESSORY = "belt_accessory"


# --- 2. Слоты Быстрого Доступа (Используются в quick_slot_position) ---
class QuickSlot(StrEnum):
    """Перечисление позиций в Quick Slot (для расходников)."""

    QUICK_SLOT_1 = "quick_slot_1"
    QUICK_SLOT_2 = "quick_slot_2"
    QUICK_SLOT_3 = "quick_slot_3"
    QUICK_SLOT_4 = "quick_slot_4"

    # Будущее: Динамический лимит N (N > 4)
    QUICK_SLOT_5 = "quick_slot_5"
    QUICK_SLOT_6 = "quick_slot_6"
    QUICK_SLOT_7 = "quick_slot_7"
    QUICK_SLOT_8 = "quick_slot_8"


class ItemType(StrEnum):
    """Перечисление возможных типов предметов."""

    WEAPON = "weapon"  # Оружие (мечи, луки, посохи)
    ARMOR = "armor"  # Броня (шлемы, нагрудники, поножи)
    ACCESSORY = "accessory"  # Аксессуары (кольца, амулеты, пояса)
    CONSUMABLE = "consumable"  # Расходники (зелья, еда)
    CONTAINER = "container"  # Контейнеры (сумки, сундуки)
    RESOURCE = "resource"  # Ресурсы (руда, травы, кожа)
    CURRENCY = "currency"  # Валюта (пыль, осколки)


class ItemRarity(StrEnum):
    """Перечисление возможных уровней редкости предметов."""

    COMMON = "common"  # Обычный
    UNCOMMON = "uncommon"  # Необычный
    RARE = "rare"  # Редкий
    EPIC = "epic"  # Эпический
    LEGENDARY = "legendary"  # Легендарный


ItemBonuses = dict[str, float | int]  # Словарь, описывающий бонусы предмета к характеристикам.


class ItemCoreData(BaseModel):
    """
    Базовые данные предмета, хранящиеся внутри JSON-поля `data` в БД.
    Эти поля общие для всех типов предметов.
    """

    name: str  # Название предмета.
    description: str  # Описание предмета.
    base_price: int  # Базовая цена предмета (для продажи/покупки у NPC).
    material: str  # Основной материал, из которого сделан предмет (например, "iron", "leather").
    bonuses: ItemBonuses = Field(default_factory=dict)  # Словарь бонусных характеристик,


class WeaponData(ItemCoreData):
    """Специфичные данные для оружия."""

    damage_min: int  # Минимальный урон, наносимый оружием.
    damage_max: int  # Максимальный урон, наносимый оружием.
    valid_slots: list[str]  # Список слотов, в которые можно экипировать оружие (например, ["main_hand", "off_hand"]).


class ArmorData(ItemCoreData):
    """Специфичные данные для брони."""

    protection: int  # Базовое значение защиты, поглощаемое броней.
    valid_slots: list[str]  # Список слотов, в которые можно экипировать броню (например, ["head", "chest"]).
    mobility_penalty: int = 0  # Штраф к мобильности/уклонению от ношения этой брони.


class AccessoryData(ItemCoreData):
    """Специфичные данные для аксессуаров."""

    valid_slots: list[str]  # Список слотов, в которые можно экипировать аксессуар (например, ["ring", "amulet"]).


class ConsumableData(ItemCoreData):
    """Специфичные данные для расходников (зелий, еды)."""

    restore_hp: int = 0
    restore_energy: int = 0
    effects: list[str] = Field(default_factory=list)
    cooldown_rounds: int = 0
    is_quick_slot_compatible: bool = False


class ResourceData(ItemCoreData):
    """Специфичные данные для ресурсов."""

    pass


class BaseInventoryItemDTO(BaseModel):
    """Общая основа для всех DTO предметов в инвентаре."""

    inventory_id: int  # Уникальный идентификатор предмета в инвентаре.
    character_id: int  # Идентификатор персонажа, которому принадлежит предмет.
    location: str  # Местонахождение предмета ("inventory", "equipped", "stash").
    subtype: str  # Подтип предмета (например, "sword", "bow").
    rarity: ItemRarity  # Редкость предмета.
    quantity: int = 1  # Количество предметов (для стакающихся).

    equipped_slot: EquippedSlot | None = None
    quick_slot_position: QuickSlot | None = None

    # Конфигурация для Pydantic
    model_config = ConfigDict(from_attributes=True)


class WeaponItemDTO(BaseInventoryItemDTO):
    """Полное DTO для оружия."""

    # Поля, которые были общими, удалены.
    item_type: Literal[ItemType.WEAPON]  # Тип предмета (строго "weapon") - ОСТАЕТСЯ КАК ДИСКРИМИНАТОР.
    data: WeaponData  # Детальные данные оружия.


class ArmorItemDTO(BaseInventoryItemDTO):
    """Полное DTO для брони."""

    item_type: Literal[ItemType.ARMOR]
    data: ArmorData


class AccessoryItemDTO(BaseInventoryItemDTO):
    """Полное DTO для аксессуаров."""

    item_type: Literal[ItemType.ACCESSORY]
    data: AccessoryData


class ConsumableItemDTO(BaseInventoryItemDTO):
    """Полное DTO для расходников."""

    item_type: Literal[ItemType.CONSUMABLE]
    data: ConsumableData


class ResourceItemDTO(BaseInventoryItemDTO):
    """Полное DTO для ресурсов и валюты."""

    item_type: Literal[ItemType.RESOURCE, ItemType.CURRENCY]
    data: ResourceData


# Полиморфный тип (остается без изменений, так как классы выше обновлены)
InventoryItemDTO = Annotated[
    WeaponItemDTO | ArmorItemDTO | AccessoryItemDTO | ConsumableItemDTO | ResourceItemDTO,
    Field(discriminator="item_type"),
]
