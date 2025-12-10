from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Mapped, declarative_base, mapped_column

Base = declarative_base()


class TimestampMixin:
    """
    Миксин для добавления полей временных меток `created_at` и `updated_at`
    к моделям SQLAlchemy.

    Эти поля автоматически управляются базой данных на уровне сервера (в UTC).
    """

    __abstract__ = True

    created_at: Mapped[datetime] = mapped_column(
        server_default=text("STRFTIME('%Y-%m-%d %H:%M:%S', 'now')"),
        nullable=False,
        comment="Время создания записи (UTC).",
    )

    updated_at: Mapped[datetime] = mapped_column(
        server_default=text("STRFTIME('%Y-%m-%d %H:%M:%S', 'now')"),
        nullable=False,
        comment="Время последнего обновления записи (UTC).",
    )
