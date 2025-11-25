# database/model_orm/symbiote.py
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.model_orm.base import Base, TimestampMixin

if TYPE_CHECKING:
    from .character import Character


class CharacterSymbiote(Base, TimestampMixin):
    """
    ORM-модель для таблицы `character_symbiotes`.

    Симбиот — это отдельная сущность, привязанная к персонажу.
    Отвечает за:
    1. Интерфейс (Имя симбиота).
    2. Магический Дар (Gift).
    3. Эволюцию (Уровень самого симбиота).
    """

    __tablename__ = "character_symbiotes"

    # Связь с персонажем (PK = FK, отношение 1:1)
    character_id: Mapped[int] = mapped_column(
        ForeignKey("characters.character_id", ondelete="CASCADE"), primary_key=True
    )

    # --- Личность Симбиота ---
    # Имя помощника (например, "Джарвис", "Веном"). По дефолту "Система".
    symbiote_name: Mapped[str] = mapped_column(String(50), default="Система", nullable=False)

    # Уровень самого симбиота (влияет на интерфейс/анализ)
    level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # --- СИСТЕМА ДАРОВ (Gift System) ---
    # Хранит ключ из GIFTS (например, "gift_true_fire")
    # nullable=True, так как на старте у игрока Дара НЕТ.
    gift_id: Mapped[str | None] = mapped_column(String(50), nullable=True, default=None)

    # Опыт Дара (накапливается при закрытии Рифтов/убийстве боссов)
    gift_xp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Ранг Дара (1-8)
    gift_rank: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Связь
    character: Mapped[Character] = relationship(back_populates="symbiote")

    def __repr__(self) -> str:
        return f"<Symbiote(char_id={self.character_id}, name='{self.symbiote_name}', gift='{self.gift_id}')>"
