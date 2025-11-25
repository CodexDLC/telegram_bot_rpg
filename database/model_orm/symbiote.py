# database/model_orm/symbiote.py
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.resources.texts.ui_messages import DEFAULT_ACTOR_NAME
from database.model_orm.base import Base, TimestampMixin

if TYPE_CHECKING:
    from .character import Character


class CharacterSymbiote(Base, TimestampMixin):
    """
    ORM-модель для таблицы `character_symbiotes`.

    Симбиот — это сущность-спутник и источник Дара (Магии).
    У него нет отдельного уровня (level), так как его развитие
    полностью синхронизировано с рангом Дара (gift_rank).
    """

    __tablename__ = "character_symbiotes"

    # Связь с персонажем (PK = FK, отношение 1:1)
    character_id: Mapped[int] = mapped_column(
        ForeignKey("characters.character_id", ondelete="CASCADE"), primary_key=True
    )

    # --- Личность Симбиота ---
    # Имя помощника. Дефолт берем из глобальной переменной (⚙️ system)
    symbiote_name: Mapped[str] = mapped_column(String(50), default=DEFAULT_ACTOR_NAME, nullable=False)

    # --- СИСТЕМА ДАРОВ (Gift System) ---
    # Поле level удалено. Прогресс определяется через gift_rank.

    # Хранит ключ из GIFTS (например, "gift_true_fire")
    # nullable=True, так как на старте у игрока Дара НЕТ.
    gift_id: Mapped[str | None] = mapped_column(String(50), nullable=True, default=None)

    # Опыт Дара (Симбиота). Накапливается при поглощении Эссенции.
    gift_xp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Ранг Дара (1-8). Это и есть фактический "Уровень" Симбиота.
    gift_rank: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Связь
    character: Mapped[Character] = relationship(back_populates="symbiote")

    def __repr__(self) -> str:
        return (
            f"<Symbiote(char_id={self.character_id}, "
            f"name='{self.symbiote_name}', "
            f"gift='{self.gift_id}', "
            f"rank={self.gift_rank})>"
        )
