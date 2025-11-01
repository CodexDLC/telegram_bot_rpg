# database/model_orm/skill_repo.py
from __future__ import annotations
from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey, String, Integer, PrimaryKeyConstraint, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.model_orm.base import Base, TimestampMixin
import enum

if TYPE_CHECKING:
    from database.model_orm.character import Characters


class SkillProgressState(enum.Enum):
    """
    Состояние прогресса навыка. включен или выключен
    """
    PLUS = "PLUS"
    PAUSE = "PAUSE"
    MINUS = "MINUS"


class CharacterSkillRate(Base):
    """
    Таблица для хранения "Базовой Ставки Опыта" (БСО)
    (Твоя 'progression_ticks', но для каждого персонажа)
    Хранит, сколько XP дается за ОДНО ДЕЙСТВИЕ или ТИК.
    """

    __tablename__ = "character_skill_rate"

    character_id: Mapped[int] = mapped_column(ForeignKey("characters.character_id", ondelete="CASCADE"))
    skill_key: Mapped[str] = mapped_column(String(50))
    xp_per_tick: Mapped[int] = mapped_column(Integer, default=0)

    character: Mapped["Characters"] = relationship(back_populates="skill_rate")

    __table_args__ = (
        PrimaryKeyConstraint("character_id", "skill_key"),
    )

class CharacterSkillProgress(Base, TimestampMixin):
    """
    Таблица для хранения текущего прогресса навыков персонажа
    (Твоя 'character_skills')
    """
    __tablename__ = "character_skill_progress"

    character_id: Mapped[int] = mapped_column(ForeignKey("characters.character_id", ondelete="CASCADE"))
    skill_key: Mapped[str] = mapped_column(String(50))
    total_xp: Mapped[int] = mapped_column(Integer, default=0)

    progress_state: Mapped[SkillProgressState] = mapped_column(
        Enum(SkillProgressState, name="skill_progress_state_enum"),
        default=SkillProgressState.PAUSE
    )

    character: Mapped["Characters"] = relationship(back_populates="skill_progress")

    __table_args__ = (
        PrimaryKeyConstraint("character_id", "skill_key"),
    )



