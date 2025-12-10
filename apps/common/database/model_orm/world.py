from __future__ import annotations

from sqlalchemy import JSON, Boolean, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.common.database.model_orm.base import Base, TimestampMixin


class WorldRegion(Base):
    """
    Макро-регион мира (15x15 клеток).
    """

    __tablename__ = "world_regions"

    id: Mapped[str] = mapped_column(String(10), primary_key=True, comment="Код региона (например, 'D4').")

    # ВОТ ЭТО ГЛАВНЫЙ ТИП РЕГИОНА (название палитры)
    biome_id: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="ID биома (например, 'wasteland', 'hub')."
    )

    # Глобальные влияния (от Якорей)
    climate_tags: Mapped[list[str]] = mapped_column(JSON, default=list, comment="Глобальные теги региона.")

    # КАРТА ПОД-ЗОН (3x3)
    # Ключ: "x_y" (0..2), Значение: "terrain_id" (конкретный тип из палитры, например 'ruins_residential')
    sector_map: Mapped[dict] = mapped_column(JSON, default=dict, comment="Карта под-зон 3x3.")

    nodes: Mapped[list[WorldGrid]] = relationship(back_populates="region")


class WorldGrid(Base, TimestampMixin):
    """
    Физическая матрица мира (105x105).
    """

    __tablename__ = "world_grid"

    # Составной первичный ключ по координатам
    x: Mapped[int] = mapped_column(Integer, primary_key=True)
    y: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Ссылка на Регион (бывший сектор)
    sector_id: Mapped[str] = mapped_column(
        ForeignKey("world_regions.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # --- STATUS FLAGS (Главный рубильник) ---
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        index=True,
        comment="True = Локация доступна игрокам и грузится в Redis. False = Туман войны.",
    )

    # --- LOGIC & MECHANICS (Источник Истины) ---
    flags: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        comment="Механика: {'is_safe_zone': true, 'has_road': true, 'biome_tags': ['forest', 'road'], 'threat_tier': 2}.",
    )

    # --- NARRATIVE & CONTENT (Для Игрока) ---
    content: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Нарратив: {'title': '...', 'description': '...', 'environment_tags': [...]}. Заполняется ЛЛМ или скриптом.",
    )

    # Ссылка на Сервис (если это вход в Данж или Арену)
    service_object_key: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="Ссылка на сервис (напр. 'svc_arena_main')."
    )

    # Связи
    region: Mapped[WorldRegion] = relationship(back_populates="nodes")

    # Индексы для оптимизации (например, поиск всех активных клеток для загрузки)
    __table_args__ = (Index("idx_world_active_path", "x", "y", "is_active"),)

    def __repr__(self) -> str:
        return f"<Node ({self.x}, {self.y}) Active={self.is_active}>"
