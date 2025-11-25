# database/model_orm/inventory.py
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import JSON, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.model_orm.base import Base

if TYPE_CHECKING:
    from .character import Character


class InventoryItem(Base):
    """
    Единая таблица для всех предметов в игре.
    Каждая строка — уникальный предмет с уникальными статами.
    """

    __tablename__ = "inventory_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    character_id: Mapped[int] = mapped_column(ForeignKey("characters.character_id", ondelete="CASCADE"), nullable=False)

    # --- Поисковые теги (чтобы быстро фильтровать в БД) ---
    # Тип предмета: weapon, armor, accessory
    item_type: Mapped[str] = mapped_column(String(20), nullable=False)

    # Подтип (для логики): sword, axe, chest_plate, ring
    # Это нужно, чтобы генератор знал, какие анимации или формулы применять
    subtype: Mapped[str] = mapped_column(String(30), nullable=False)

    # Редкость: common, rare, epic, legendary (влияет на цвет в чате и силу)
    rarity: Mapped[str] = mapped_column(String(20), default="common")

    # Где лежит: inventory, equipped, auction, bank
    location: Mapped[str] = mapped_column(String(20), default="inventory")

    quantity: Mapped[int] = mapped_column(Integer, default=1)

    # --- JSON "PAYLOAD" ---
    # Здесь лежит ВСЁ остальное:
    # - name, description (от ИИ)
    # - stats (урон, защита)
    # - bonuses (словарь +сила, +крит)
    # - durability, enchant_level

    # 🔥 ИСПРАВЛЕНИЕ ЗДЕСЬ: default_factory -> default
    item_data: Mapped[dict] = mapped_column(JSON, default=dict)

    # Связь
    character: Mapped[Character] = relationship(back_populates="inventory")

    def __repr__(self):
        return f"<Item {self.id} ({self.rarity} {self.subtype})>"
