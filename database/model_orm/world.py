from sqlalchemy import JSON, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from database.model_orm.base import Base, TimestampMixin


class WorldNode(Base, TimestampMixin):
    __tablename__ = "world_nodes"

    # Координаты - наш главный идентификатор
    x: Mapped[int] = mapped_column(Integer, nullable=False)
    y: Mapped[int] = mapped_column(Integer, nullable=False)

    # "Регион" (например, "city_center", "north_forest", "wasteland")
    # Это нужно, чтобы знать, какой промпт слать LLM.
    biome_id: Mapped[str] = mapped_column(String(50), nullable=False)

    # Тип узла: "empty", "road", "poi" (интересное место), "rift_entrance"
    node_type: Mapped[str] = mapped_column(String(20), default="empty")

    # Сгенерированный контент (Название, Описание, Картинка)
    content: Mapped[dict] = mapped_column(JSON, default=dict)

    # Кто владеет землей (на будущее)
    owner_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Уникальность координат (нельзя создать две ноды в 10:10)
    __table_args__ = (UniqueConstraint("x", "y", name="uix_coordinates"),)
