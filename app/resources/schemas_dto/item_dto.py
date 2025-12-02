"""
Модуль содержит DTO (Data Transfer Objects) для работы с игровыми предметами.

Определяет базовые типы предметов, их редкость, а также детальные
структуры данных для различных категорий предметов (оружие, броня,
аксессуары, расходники, ресурсы) и их полиморфное представление.
"""

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, Field


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
    weight: float  # Вес предмета (влияет на переносимый вес персонажа).
    material: str  # Основной материал, из которого сделан предмет (например, "iron", "leather").
    bonuses: ItemBonuses = Field(default_factory=dict)  # Словарь бонусных характеристик,
    # которые предмет дает персонажу (например, {"strength": 5, "hp_max": 10}).


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

    restore_hp: int = 0  # Количество HP, восстанавливаемое при использовании.
    restore_energy: int = 0  # Количество энергии, восстанавливаемое при использовании.
    effects: list[str] = Field(default_factory=list)  # Список эффектов, накладываемых при использовании.


class ResourceData(ItemCoreData):
    """Специфичные данные для ресурсов."""

    pass  # Ресурсы могут не иметь дополнительных специфичных полей, кроме базовых.


class WeaponItemDTO(BaseModel):
    """Полное DTO для оружия, включая данные из БД и `ItemCoreData`."""

    inventory_id: int  # Уникальный идентификатор предмета в инвентаре.
    character_id: int  # Идентификатор персонажа, которому принадлежит предмет.
    location: str  # Местонахождение предмета ("inventory", "equipped", "stash").
    item_type: Literal[ItemType.WEAPON]  # Тип предмета (строго "weapon").
    subtype: str  # Подтип оружия (например, "sword", "bow").
    rarity: ItemRarity  # Редкость предмета.
    data: WeaponData  # Детальные данные оружия.
    quantity: int = 1  # Количество предметов (для стакающихся).


class ArmorItemDTO(BaseModel):
    """Полное DTO для брони."""

    inventory_id: int  # Уникальный идентификатор предмета в инвентаре.
    character_id: int  # Идентификатор персонажа, которому принадлежит предмет.
    location: str  # Местонахождение предмета.
    item_type: Literal[ItemType.ARMOR]  # Тип предмета (строго "armor").
    subtype: str  # Подтип брони (например, "heavy", "light").
    rarity: ItemRarity  # Редкость предмета.
    data: ArmorData  # Детальные данные брони.
    quantity: int = 1  # Количество предметов.


class AccessoryItemDTO(BaseModel):
    """Полное DTO для аксессуаров."""

    inventory_id: int  # Уникальный идентификатор предмета в инвентаре.
    character_id: int  # Идентификатор персонажа, которому принадлежит предмет.
    location: str  # Местонахождение предмета.
    item_type: Literal[ItemType.ACCESSORY]  # Тип предмета (строго "accessory").
    subtype: str  # Подтип аксессуара (например, "ring", "amulet").
    rarity: ItemRarity  # Редкость предмета.
    data: AccessoryData  # Детальные данные аксессуара.
    quantity: int = 1  # Количество предметов.


class ConsumableItemDTO(BaseModel):
    """Полное DTO для расходников."""

    inventory_id: int  # Уникальный идентификатор предмета в инвентаре.
    character_id: int  # Идентификатор персонажа, которому принадлежит предмет.
    location: str  # Местонахождение предмета.
    item_type: Literal[ItemType.CONSUMABLE]  # Тип предмета (строго "consumable").
    subtype: str  # Подтип расходника (например, "potion_hp", "food_ration").
    rarity: ItemRarity  # Редкость предмета.
    data: ConsumableData  # Детальные данные расходника.
    quantity: int  # Количество предметов.


class ResourceItemDTO(BaseModel):
    """Полное DTO для ресурсов и валюты."""

    inventory_id: int  # Уникальный идентификатор предмета в инвентаре.
    character_id: int  # Идентификатор персонажа, которому принадлежит предмет.
    location: str  # Местонахождение предмета.
    item_type: Literal[ItemType.RESOURCE, ItemType.CURRENCY]  # Тип предмета (строго "resource" или "currency").
    subtype: str  # Подтип ресурса (например, "ore", "dust").
    rarity: ItemRarity  # Редкость предмета.
    data: ResourceData  # Детальные данные ресурса.
    quantity: int  # Количество предметов.


# Полиморфный тип для любого предмета в инвентаре.
InventoryItemDTO = Annotated[
    WeaponItemDTO | ArmorItemDTO | AccessoryItemDTO | ConsumableItemDTO | ResourceItemDTO,
    Field(discriminator="item_type"),
]
