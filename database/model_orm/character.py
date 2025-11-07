# database/model_orm/character.py
from __future__ import annotations
from typing import TYPE_CHECKING, List
from sqlalchemy import ForeignKey, String, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.model_orm.base import Base, TimestampMixin

if TYPE_CHECKING:
    from .user import User
    from .skill import CharacterSkillRate, CharacterSkillProgress


class Character(Base, TimestampMixin):
    """
    ORM-модель для таблицы `characters`.

    Представляет игрового персонажа, созданного пользователем.

    Attributes:
        character_id (Mapped[int]): Уникальный ID персонажа (первичный ключ).
        user_id (Mapped[int]): ID пользователя-владельца (внешний ключ к `users`).
        name (Mapped[str]): Имя персонажа.
        gender (Mapped[str]): Пол персонажа.
        game_stage (Mapped[str]): Текущий этап игры или состояние персонажа
            (например, 'creation', 'tutorial', 'main_game').

        user (Mapped["User"]): Связь "многие-к-одному" с моделью User.
            Позволяет получить доступ к объекту пользователя-владельца.
        stats (Mapped["CharacterStats"]): Связь "один-к-одному" с характеристиками
            персонажа.
        skill_rate (Mapped[List["CharacterSkillRate"]]): Связь "один-ко-многим"
            со ставками навыков персонажа.
        skill_progress (Mapped[List["CharacterSkillProgress"]]): Связь "один-ко-многим"
            с прогрессом навыков персонажа.

        created_at, updated_at: Временные метки (наследуются от TimestampMixin).
    """
    __tablename__ = "characters"

    character_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # ondelete="CASCADE" означает, что при удалении пользователя
    # все его персонажи также будут удалены на уровне БД.
    user_id: Mapped[int] = mapped_column(ForeignKey("users.telegram_id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), default="Новый персонаж", nullable=False)
    gender: Mapped[str] = mapped_column(String(20), default="other", nullable=False)
    game_stage: Mapped[str] = mapped_column(String(50), default="creation", nullable=False)

    # Связи
    user: Mapped["User"] = relationship(back_populates="characters")
    stats: Mapped["CharacterStats"] = relationship(
        back_populates="character",
        cascade="all, delete-orphan"  # При удалении персонажа удаляются и его статы
    )
    skill_rate: Mapped[List["CharacterSkillRate"]] = relationship(
        back_populates="character",
        cascade="all, delete-orphan"
    )
    skill_progress: Mapped[List["CharacterSkillProgress"]] = relationship(
        back_populates="character",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Character(id={self.character_id}, name='{self.name}', user_id={self.user_id})>"


class CharacterStats(Base, TimestampMixin):
    """
    ORM-модель для таблицы `character_stats`.

    Хранит основные характеристики (S.P.E.C.I.A.L.) персонажа.
    Связана с `Character` отношением "один-к-одному".

    Attributes:
        character_id (Mapped[int]): ID персонажа (первичный и внешний ключ).
        strength, perception, endurance, charisma, intelligence, agility, luck:
            Числовые значения характеристик.

        character (Mapped["Character"]): Обратная связь "один-к-одному" с моделью
            Character.

        created_at, updated_at: Временные метки (наследуются от TimestampMixin).
    """
    __tablename__ = "character_stats"

    # `character_id` является одновременно и первичным, и внешним ключом,
    # что обеспечивает связь "один-к-одному".
    character_id: Mapped[int] = mapped_column(
        ForeignKey("characters.character_id", ondelete="CASCADE"),
        primary_key=True
    )
    strength: Mapped[int] = mapped_column(Integer, default=4, nullable=False)
    perception: Mapped[int] = mapped_column(Integer, default=4, nullable=False)
    endurance: Mapped[int] = mapped_column(Integer, default=4, nullable=False)
    charisma: Mapped[int] = mapped_column(Integer, default=4, nullable=False)
    intelligence: Mapped[int] = mapped_column(Integer, default=4, nullable=False)
    agility: Mapped[int] = mapped_column(Integer, default=4, nullable=False)
    luck: Mapped[int] = mapped_column(Integer, default=4, nullable=False)

    # Обратная связь
    character: Mapped["Character"] = relationship(back_populates="stats")

    def __repr__(self) -> str:
        return f"<CharacterStats(character_id={self.character_id})>"
