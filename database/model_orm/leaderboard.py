# database/model_orm/leaderboard.py
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.model_orm.base import Base, TimestampMixin

if TYPE_CHECKING:
    from .character import Character


class Leaderboard(Base, TimestampMixin):
    """
    Таблица для хранения агрегированной статистики и рейтингов.
    Используется для матчмейкинга (поиск по GS) и веб-лидербордов.
    """

    __tablename__ = "leaderboards"

    character_id: Mapped[int] = mapped_column(
        ForeignKey("characters.character_id", ondelete="CASCADE"), primary_key=True
    )

    # 🔥 Тот самый Gear Score (с индексом для поиска)
    gear_score: Mapped[int] = mapped_column(Integer, default=0, index=True)

    # Задел на будущее (Твои идеи про опыт и ранги)
    total_xp: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    pvp_rating: Mapped[int] = mapped_column(Integer, default=1000, index=True)  # ELO / MMR

    # Связь (чтобы ORM знала)
    character: Mapped[Character] = relationship(backref="leaderboard")

    def __repr__(self) -> str:
        return f"<Leaderboard(char_id={self.character_id}, gs={self.gear_score})>"
