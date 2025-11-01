# database/model_orm/user.py
from __future__ import annotations
from typing import TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.model_orm.base import TimestampMixin, Base

if TYPE_CHECKING:
    from .character import Characters

class User(Base, TimestampMixin):

    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str]
    username: Mapped[str | None]
    last_name: Mapped[str | None]
    language_code: Mapped[str] = mapped_column(default="ru")
    is_premium: Mapped[bool] = mapped_column(default=False)

    characters: Mapped[list["Characters"]] = relationship(back_populates="user")

    def __repr__(self) -> str:
        return f"<User (id={self.telegram_id}, name='{self.first_name}')>"



