from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import JSON, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.common.database.model_orm.base import Base

if TYPE_CHECKING:
    from .character import Character


class InventoryItem(Base):
    """
    ORM-модель для таблицы `inventory_items`.

    Представляет уникальный предмет в инвентаре персонажа,
    храня его основные свойства и детальные данные в JSON-поле.
    """

    __tablename__ = "inventory_items"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="Уникальный идентификатор предмета в инвентаре."
    )
    character_id: Mapped[int] = mapped_column(
        ForeignKey("characters.character_id", ondelete="CASCADE"),
        nullable=False,
        comment="Идентификатор персонажа, которому принадлежит предмет.",
    )
    item_type: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="Тип предмета (например, 'weapon', 'armor', 'accessory')."
    )
    subtype: Mapped[str] = mapped_column(
        String(30), nullable=False, comment="Подтип предмета (например, 'sword', 'chest_plate', 'ring')."
    )
    rarity: Mapped[str] = mapped_column(
        String(20), default="common", comment="Редкость предмета (например, 'common', 'rare', 'epic')."
    )
    location: Mapped[str] = mapped_column(
        String(20),
        default="inventory",
        comment="Местонахождение предмета ('inventory', 'equipped', 'auction', 'bank').",
    )
    quantity: Mapped[int] = mapped_column(
        Integer, default=1, comment="Количество предметов (для стакающихся предметов)."
    )
    item_data: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        comment="JSON-поле, содержащее детальные данные предмета (название, описание, статы, бонусы).",
    )

    equipped_slot: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="Слот экипировки (head_armor, ring_1, etc.)."
    )

    quick_slot_position: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="Позиция в быстром доступе (quick_slot_1, etc.)."
    )

    character: Mapped[Character] = relationship(back_populates="inventory")

    def __repr__(self):
        return f"<Item {self.id} ({self.rarity} {self.subtype})>"


class ResourceWallet(Base):
    """
    ORM-модель для таблицы `resource_wallets`.

    Представляет "пространственный карман" персонажа для хранения ресурсов,
    сгруппированных по категориям.
    """

    __tablename__ = "resource_wallets"

    character_id: Mapped[int] = mapped_column(
        ForeignKey("characters.character_id", ondelete="CASCADE"),
        primary_key=True,
        comment="Идентификатор персонажа (первичный и внешний ключ).",
    )

    currency: Mapped[dict] = mapped_column(
        JSON, default=dict, comment="Словарь для хранения валюты (например, 'dust', 'shard')."
    )
    ores: Mapped[dict] = mapped_column(JSON, default=dict, comment="Словарь для хранения руд и камней.")
    leathers: Mapped[dict] = mapped_column(JSON, default=dict, comment="Словарь для хранения шкур и кожи.")
    fabrics: Mapped[dict] = mapped_column(JSON, default=dict, comment="Словарь для хранения тканей и ниток.")
    organics: Mapped[dict] = mapped_column(
        JSON, default=dict, comment="Словарь для хранения трав, еды, частей монстров."
    )
    parts: Mapped[dict] = mapped_column(JSON, default=dict, comment="Словарь для хранения компонентов и эссенций.")

    character: Mapped[Character] = relationship("Character", back_populates="wallet")

    def __repr__(self):
        return f"<Wallet char_id={self.character_id}>"
