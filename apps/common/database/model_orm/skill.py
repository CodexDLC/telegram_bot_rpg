from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Enum, Float, ForeignKey, PrimaryKeyConstraint, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.common.database.model_orm.base import Base, TimestampMixin

if TYPE_CHECKING:
    from .character import Character


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


class CharacterSkillProgress(Base, TimestampMixin):
    """
    ORM-модель для таблицы `character_skill_progress`.

    Отслеживает текущий прогресс (общий опыт и состояние) каждого навыка
    у конкретного персонажа.
    """

    __tablename__ = "character_skill_progress"

    character_id: Mapped[int] = mapped_column(
        ForeignKey("characters.character_id", ondelete="CASCADE"),
        nullable=False,
        comment="Идентификатор персонажа (часть составного первичного ключа).",
    )
    skill_key: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="Уникальный строковый ключ навыка (часть составного первичного ключа)."
    )

    # Общий опыт (Float)
    # Храним только результат. Скорость (Rate) считается динамически и кешируется в Redis.
    total_xp: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False, comment="Общее количество опыта, накопленного в навыке."
    )

    is_unlocked: Mapped[bool] = mapped_column(
        default=False, nullable=False, comment="Флаг, указывающий, разблокирован ли навык для использования."
    )

    progress_state: Mapped[SkillProgressState] = mapped_column(
        Enum(SkillProgressState, name="skill_progress_state_enum", create_type=True),
        default=SkillProgressState.PAUSE,
        nullable=False,
        comment="Текущее состояние развития навыка (PLUS, PAUSE, MINUS).",
    )

    character: Mapped[Character] = relationship(back_populates="skill_progress")

    __table_args__ = (PrimaryKeyConstraint("character_id", "skill_key", name="pk_character_skill_progress"),)

    def __repr__(self) -> str:
        return f"<CharacterSkillProgress(char_id={self.character_id}, skill='{self.skill_key}', xp={self.total_xp})>"
