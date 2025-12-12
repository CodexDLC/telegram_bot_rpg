# app/common/database/model_orm/world.py

from __future__ import annotations

from sqlalchemy import JSON, Boolean, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.common.database.model_orm.base import Base, TimestampMixin


# ----------------------------------------------------------------------
# УРОВЕНЬ 1: РЕГИОН (15x15)
# Контейнер для изоляции и глобальных эффектов.
# ----------------------------------------------------------------------
class WorldRegion(Base):
    __tablename__ = "world_regions"

    # ID региона, например "D4".
    id: Mapped[str] = mapped_column(String(10), primary_key=True)

    # Глобальные теги (погода, атмосфера, магия).
    # Влияют на описание всех зон внутри.
    climate_tags: Mapped[list[str]] = mapped_column(JSON, default=list)

    # Связь вниз: Один Регион -> Много Зон
    zones: Mapped[list[WorldZone]] = relationship(back_populates="region")


# ----------------------------------------------------------------------
# УРОВЕНЬ 2: ЗОНА (5x5)
# Владелец Биома. Определяет палитру.
# ----------------------------------------------------------------------
class WorldZone(Base):
    __tablename__ = "world_zones"

    # Уникальный ID зоны, например "D4_1_1" (Region_X_Y внутри региона).
    id: Mapped[str] = mapped_column(String(20), primary_key=True)

    # Ссылка на родителя (Регион)
    region_id: Mapped[str] = mapped_column(
        ForeignKey("world_regions.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # БИОМ (Главный ключ словаря конфига)
    # Пример: "forest", "wasteland", "swamp"
    # Говорит генератору, какую палитру использовать для нод.
    biome_id: Mapped[str] = mapped_column(String(50), nullable=False)

    # Связи
    region: Mapped[WorldRegion] = relationship(back_populates="zones")
    nodes: Mapped[list[WorldGrid]] = relationship(back_populates="zone")


# ----------------------------------------------------------------------
# УРОВЕНЬ 3: НОДА / КЛЕТКА (1x1)
# Конкретная физическая точка мира.
# ----------------------------------------------------------------------
class WorldGrid(Base, TimestampMixin):
    __tablename__ = "world_grid"

    # Координаты (Primary Key)
    x: Mapped[int] = mapped_column(Integer, primary_key=True)
    y: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Ссылка на Зону (5x5)
    zone_id: Mapped[str] = mapped_column(ForeignKey("world_zones.id", ondelete="CASCADE"), nullable=False, index=True)

    # 1. ТИП МЕСТНОСТИ (Sub-Type / Terrain Key)
    terrain_type: Mapped[str] = mapped_column(String(50), nullable=False)

    # 2. СПИСОК СЕРВИСОВ
    # Хранит список ключей сервисов, доступных в этой клетке.
    # Например: ["svc_arena_main", "svc_blacksmith_repair"]
    services: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)

    # 3. НАРРАТИВ (Генерация LLM)
    content: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, comment="{'title': '...', 'description': '...', 'tags': [...]}"
    )

    # 4. ТЕХНИЧЕСКИЕ ФЛАГИ
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    flags: Mapped[dict] = mapped_column(JSON, default=dict)

    # Связи
    zone: Mapped[WorldZone] = relationship(back_populates="nodes")

    # Индекс для ускорения выборки активных клеток при старте сервера
    __table_args__ = (Index("idx_world_active_path", "x", "y", "is_active"),)

    def __repr__(self) -> str:
        return f"<Node ({self.x}, {self.y}) Type={self.terrain_type}>"
