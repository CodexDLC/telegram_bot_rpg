# database/model_orm/user.py
from __future__ import annotations
from typing import TYPE_CHECKING, List
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import BigInteger, String

from database.model_orm.base import TimestampMixin, Base

if TYPE_CHECKING:
    from .character import Character  # Изменено на единственное число для соответствия PEP-8


class User(Base, TimestampMixin):
    """
    ORM-модель для таблицы `users`.

    Представляет пользователя Telegram в системе.

    Attributes:
        telegram_id (Mapped[int]): Уникальный идентификатор пользователя в Telegram.
            Используется как первичный ключ. Тип `BigInteger` для совместимости
            с 64-битными ID.
        first_name (Mapped[str]): Имя пользователя.
        username (Mapped[str | None]): Никнейм пользователя в Telegram (может отсутствовать).
        last_name (Mapped[str | None]): Фамилия пользователя (может отсутствовать).
        language_code (Mapped[str]): Языковой код, полученный от Telegram.
            По умолчанию 'ru'.
        is_premium (Mapped[bool]): Флаг, указывающий, является ли пользователь
            подписчиком Telegram Premium. По умолчанию False.

        characters (Mapped[List["Character"]]): Связь "один-ко-многим" с моделями
            персонажей. Позволяет получить список всех персонажей, созданных
            этим пользователем.

        created_at (Mapped[str]): Время создания записи (наследуется от TimestampMixin).
        updated_at (Mapped[str]): Время последнего обновления (наследуется от TimestampMixin).
    """
    __tablename__ = "users"

    # Явно указываем типы данных для лучшей совместимости с PostgreSQL
    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    first_name: Mapped[str] = mapped_column(String(64))
    username: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    language_code: Mapped[str] = mapped_column(String(10), default="ru", nullable=False)
    is_premium: Mapped[bool] = mapped_column(default=False, nullable=False)

    # Связь с персонажами. `back_populates` обеспечивает двустороннюю связь.
    characters: Mapped[List["Character"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"  # При удалении юзера удаляются и его персонажи
    )

    def __repr__(self) -> str:
        """
        Возвращает строковое представление объекта User.
        """
        return (f"<User(telegram_id={self.telegram_id}, "
                f"first_name='{self.first_name}', username='{self.username}')>")
