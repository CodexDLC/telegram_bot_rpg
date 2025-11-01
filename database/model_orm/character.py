# database/model_orm/character.py
from __future__ import annotations
from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.model_orm.base import Base, TimestampMixin

if TYPE_CHECKING:
    from .user import User

class Characters(Base, TimestampMixin):
    __tablename__ = "characters"

    character_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.telegram_id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(default="Новый персонаж")
    gender: Mapped[str] = mapped_column(default="other")
    game_stage: Mapped[str] = mapped_column(default="creation")

    stats: Mapped["CharacterStats"] = relationship(back_populates="character")

    user: Mapped["User"] = relationship(back_populates="characters")

    def __repr__(self):
        return f"<Character (id={self.character_id}, name='{self.name}')>"


class CharacterStats(Base, TimestampMixin):

    __tablename__ = "character_stats"

    character_id: Mapped[int] = mapped_column(ForeignKey("characters.character_id", ondelete="CASCADE"), primary_key=True)
    strength: Mapped[int] = mapped_column(default=4)
    perception: Mapped[int] = mapped_column(default=4)
    endurance: Mapped[int] = mapped_column(default=4)
    charisma: Mapped[int] = mapped_column(default=4)
    intelligence: Mapped[int] = mapped_column(default=4)
    agility: Mapped[int] = mapped_column(default=4)
    luck: Mapped[int] = mapped_column(default=4)

    character: Mapped["Characters"] = relationship("stats")

    def __repr__(self):
        return f"<CharacterStats (id={self.character_id})>"