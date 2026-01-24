from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel, Field

from common.schemas.item import InventoryItemDTO


class WalletDTO(BaseModel):
    """
    DTO для кошелька ресурсов.
    Хранит только те ресурсы, которые есть у игрока (>0).
    """

    currency: dict[str, int] = Field(default_factory=dict)
    resources: dict[str, int] = Field(default_factory=dict)
    components: dict[str, int] = Field(default_factory=dict)


class InventorySessionDTO(BaseModel):
    """
    DTO для хранения сессии инвентаря в Redis/Memory.
    Максимально компактное представление состояния.
    """

    # Предметы (Оружие, Броня, Расходники)
    # Key: inventory_id (int)
    items: dict[int, InventoryItemDTO] = Field(default_factory=dict)

    # Ресурсы (Валюта, Материалы)
    wallet: WalletDTO = Field(default_factory=WalletDTO)

    # Метаданные (Кэш статов, лимиты)
    stats: dict[str, Any] = Field(default_factory=dict)


# --- RESPONSE DTOs (Ответы от Core к UI) ---


class InventoryMainMenuResponseDTO(BaseModel):
    """Данные для главного экрана (Кукла + Сводка)."""

    summary: dict[str, int]  # weight, max_weight, dust, gold
    equipped: list[InventoryItemDTO]


class InventoryBagResponseDTO(BaseModel):
    """Данные для списка предметов (Сумка/Фильтр)."""

    items: Sequence[InventoryItemDTO]
    page: int
    total_pages: int
    section: str  # equip, resource, consumable
    category: str | None  # slot name or subtype
    title: str  # Заголовок для UI (опционально, или UI сам решит)


class InventoryItemDetailsResponseDTO(BaseModel):
    """Данные для просмотра конкретного предмета."""

    item: InventoryItemDTO
    actions: list[str]  # Список доступных действий: ['equip', 'drop', 'use', 'quick_slot']
    comparison: InventoryItemDTO | None = None  # Предмет, с которым сравниваем (надетый в этот слот)
