from __future__ import annotations

from sqlalchemy import JSON, Boolean, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.model_orm.base import Base


class WorldSector(Base):
    """
    Конфигурация макро-регионов (7x7).
    Заполняется статично (49 записей).
    """

    __tablename__ = "world_sectors"

    id: Mapped[str] = mapped_column(String(10), primary_key=True, comment="Код сектора (например, 'D4', 'A1').")
    tier: Mapped[int] = mapped_column(Integer, default=1, nullable=False, comment="Уровень сложности мобов (0-5).")
    biome_id: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="ID биома ('forest', 'ruins', 'fire_waste'). Влияет на генерацию."
    )
    anchor_type: Mapped[str] = mapped_column(
        String(20), default="WILD", comment="Тип якоря (HUB, OUTPOST, RIFT_ENTRY, WILD)."
    )

    # Связь с клетками
    nodes: Mapped[list[WorldGrid]] = relationship(back_populates="sector")

    def __repr__(self) -> str:
        return f"<Sector {self.id} (Tier {self.tier})>"


class WorldGrid(Base):
    """
    Физическая матрица мира (105x105).
    """

    __tablename__ = "world_grid"

    # Составной первичный ключ по координатам
    x: Mapped[int] = mapped_column(Integer, primary_key=True)
    y: Mapped[int] = mapped_column(Integer, primary_key=True)

    sector_id: Mapped[str] = mapped_column(
        ForeignKey("world_sectors.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # --- STATUS FLAGS ---
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        index=True,
        comment="True = Локация доступна игрокам и грузится в Redis. False = Туман войны.",
    )

    # --- CONTENT & LOGIC ---
    service_object_key: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="Ссылка на сервис (напр. 'svc_arena_main'). Если NULL - обычная локация."
    )

    flags: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        comment="Локальные правила и свойства: {'is_safe_zone': true, 'has_road': true, 'rift_id': '...'}",
    )

    content: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, comment="Сгенерированный контент (Название, Описание, Теги). NULL если не активно."
    )

    # Связи
    sector: Mapped[WorldSector] = relationship(back_populates="nodes")

    # Индексы для оптимизации
    __table_args__ = (
        # Индекс для быстрого поиска активных соседей (Pathfinder)
        Index("idx_world_active_path", "x", "y", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<Node ({self.x}, {self.y}) Active={self.is_active}>"
