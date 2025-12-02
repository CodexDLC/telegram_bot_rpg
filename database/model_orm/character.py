from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.model_orm.base import Base, TimestampMixin

if TYPE_CHECKING:
    from .inventory import InventoryItem, ResourceWallet
    from .skill import CharacterSkillProgress, CharacterSkillRate
    from .symbiote import CharacterSymbiote
    from .user import User


class Character(Base, TimestampMixin):
    """
    ORM-модель для таблицы `characters`.

    Представляет игрового персонажа, созданного пользователем,
    и связывает его со всеми игровыми данными.
    """

    __tablename__ = "characters"

    character_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="Уникальный идентификатор персонажа."
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        nullable=False,
        comment="Идентификатор пользователя Telegram, которому принадлежит персонаж.",
    )
    name: Mapped[str] = mapped_column(String(100), default="Новый персонаж", nullable=False, comment="Имя персонажа.")
    gender: Mapped[str] = mapped_column(String(20), default="other", nullable=False, comment="Пол персонажа.")
    game_stage: Mapped[str] = mapped_column(
        String(50),
        default="creation",
        nullable=False,
        comment="Текущий этап игры или состояние персонажа (например, 'creation', 'tutorial', 'in_game').",
    )

    user: Mapped[User] = relationship(
        back_populates="characters", comment="Обратная связь с моделью User (владелец персонажа)."
    )
    stats: Mapped[CharacterStats] = relationship(
        back_populates="character",
        cascade="all, delete-orphan",
        comment="Характеристики персонажа (связь один-к-одному).",
    )
    skill_rate: Mapped[list[CharacterSkillRate]] = relationship(
        back_populates="character",
        cascade="all, delete-orphan",
        comment="Ставки опыта навыков персонажа (связь один-ко-многим).",
    )
    skill_progress: Mapped[list[CharacterSkillProgress]] = relationship(
        back_populates="character",
        cascade="all, delete-orphan",
        comment="Прогресс навыков персонажа (связь один-ко-многим).",
    )
    symbiote: Mapped[CharacterSymbiote] = relationship(
        back_populates="character",
        cascade="all, delete-orphan",
        uselist=False,
        comment="Симбиот персонажа (связь один-к-одному).",
    )
    inventory: Mapped[list[InventoryItem]] = relationship(
        back_populates="character", cascade="all, delete-orphan", comment="Инвентарь персонажа (связь один-ко-многим)."
    )
    wallet: Mapped[ResourceWallet] = relationship(
        back_populates="character",
        cascade="all, delete-orphan",
        uselist=False,
        comment="Кошелек ресурсов персонажа (связь один-к-одному).",
    )

    def __repr__(self) -> str:
        return f"<Character(id={self.character_id}, name='{self.name}', user_id={self.user_id})>"


class CharacterStats(Base, TimestampMixin):
    """
    ORM-модель для таблицы `character_stats`.

    Хранит основные характеристики персонажа.
    Связана с `Character` отношением "один-к-одному".
    """

    __tablename__ = "character_stats"

    character_id: Mapped[int] = mapped_column(
        ForeignKey("characters.character_id", ondelete="CASCADE"),
        primary_key=True,
        comment="Идентификатор персонажа (первичный и внешний ключ).",
    )
    strength: Mapped[int] = mapped_column(
        Integer, default=4, nullable=False, comment="Сила: влияет на физический урон, переносимый вес."
    )
    agility: Mapped[int] = mapped_column(
        Integer, default=4, nullable=False, comment="Ловкость: влияет на уклонение, точность, скорость атаки."
    )
    endurance: Mapped[int] = mapped_column(
        Integer, default=4, nullable=False, comment="Выносливость: влияет на максимальное HP, физическое сопротивление."
    )
    intelligence: Mapped[int] = mapped_column(
        Integer, default=4, nullable=False, comment="Интеллект: влияет на магический урон, эффективность заклинаний."
    )
    wisdom: Mapped[int] = mapped_column(
        Integer,
        default=4,
        nullable=False,
        comment="Мудрость: влияет на магическое сопротивление, шанс крита заклинаний.",
    )
    men: Mapped[int] = mapped_column(
        Integer, default=4, nullable=False, comment="Дух: влияет на максимальную энергию/ману, сопротивление контролю."
    )
    perception: Mapped[int] = mapped_column(
        Integer,
        default=4,
        nullable=False,
        comment="Восприятие: влияет на шанс найти лут, обнаружение ловушек, слоты инвентаря.",
    )
    charisma: Mapped[int] = mapped_column(
        Integer,
        default=4,
        nullable=False,
        comment="Харизма: влияет на цены у торговцев, эффективность питомцев, социальные навыки.",
    )
    luck: Mapped[int] = mapped_column(
        Integer, default=4, nullable=False, comment="Удача: влияет на шанс крита, шанс найти лут, успех крафта."
    )

    character: Mapped[Character] = relationship(back_populates="stats", comment="Обратная связь с моделью Character.")

    def __repr__(self) -> str:
        return f"<CharacterStats(character_id={self.character_id})>"
