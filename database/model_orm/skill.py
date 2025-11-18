# database/model_orm/skill.py
from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Integer, PrimaryKeyConstraint, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.model_orm.base import Base, TimestampMixin

if TYPE_CHECKING:
    from .character import Character  # Изменено на единственное число


class SkillProgressState(enum.Enum):
    """
    Перечисление, определяющее состояние развития навыка.

    - PLUS: Навык активно развивается (например, получает бонусный опыт).
    - PAUSE: Развитие навыка приостановлено.
    - MINUS: Развитие навыка замедлено или регрессирует.
    """

    PLUS = "PLUS"
    PAUSE = "PAUSE"
    MINUS = "MINUS"


class CharacterSkillRate(Base):
    """
    ORM-модель для таблицы `character_skill_rate`.

    Хранит "Базовую Ставку Опыта" (БСО) для каждого навыка у персонажа.
    Это значение определяет, сколько опыта (`xp_per_tick`) начисляется за
    одно условное действие или "тик" времени.

    Attributes:
        character_id (Mapped[int]): ID персонажа (часть составного первичного ключа).
        skill_key (Mapped[str]): Уникальный строковый ключ навыка
            (например, 'strength_athletics'). Часть составного первичного ключа.
        xp_per_tick (Mapped[int]): Количество опыта, начисляемого за "тик".

        character (Mapped["Character"]): Обратная связь с моделью Character.
    """

    __tablename__ = "character_skill_rate"

    character_id: Mapped[int] = mapped_column(ForeignKey("characters.character_id", ondelete="CASCADE"), nullable=False)
    skill_key: Mapped[str] = mapped_column(String(50), nullable=False)
    xp_per_tick: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    character: Mapped[Character] = relationship(back_populates="skill_rate")

    # Составной первичный ключ гарантирует, что для одного персонажа
    # может быть только одна запись для каждого навыка.
    __table_args__ = (PrimaryKeyConstraint("character_id", "skill_key"),)

    def __repr__(self) -> str:
        return (
            f"<CharacterSkillRate(char_id={self.character_id}, skill='{self.skill_key}', xp_rate={self.xp_per_tick})>"
        )


class CharacterSkillProgress(Base, TimestampMixin):
    """
    ORM-модель для таблицы `character_skill_progress`.

    Отслеживает текущий прогресс (общий опыт и состояние) каждого навыка
    у конкретного персонажа.

    Attributes:
        character_id (Mapped[int]): ID персонажа (часть составного ключа).
        skill_key (Mapped[str]): Ключ навыка (часть составного ключа).
        total_xp (Mapped[int]): Общее количество опыта, накопленного в навыке.
        progress_state (Mapped[SkillProgressState]): Текущее состояние развития
            навыка (PLUS, PAUSE, MINUS).

        character (Mapped["Character"]): Обратная связь с моделью Character.
        created_at, updated_at: Временные метки.
    """

    __tablename__ = "character_skill_progress"

    character_id: Mapped[int] = mapped_column(ForeignKey("characters.character_id", ondelete="CASCADE"), nullable=False)
    skill_key: Mapped[str] = mapped_column(String(50), nullable=False)
    total_xp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_unlocked: Mapped[bool] = mapped_column(default=False, nullable=False)

    progress_state: Mapped[SkillProgressState] = mapped_column(
        Enum(SkillProgressState, name="skill_progress_state_enum", create_type=True),
        default=SkillProgressState.PAUSE,
        nullable=False,
    )

    character: Mapped[Character] = relationship(back_populates="skill_progress")

    __table_args__ = (PrimaryKeyConstraint("character_id", "skill_key"),)

    def __repr__(self) -> str:
        return (
            f"<CharacterSkillProgress(char_id={self.character_id}, "
            f"skill='{self.skill_key}', xp={self.total_xp}, "
            f"state='{self.progress_state.name}')>"
        )
