# database/model_orm/base.py
from sqlalchemy import text
from sqlalchemy.orm import (
    declarative_base,
    Mapped,
    mapped_column
)

Base = declarative_base()

class TimestampMixin:
    """
        Mixin для добавления created_at и updated_at.
    """

    created_at: Mapped[str] = mapped_column(
        server_default=text("STRFTIME('%Y-%m-%d %H:%M:%f', 'now')"))
    updated_at: Mapped[str] = mapped_column(
        server_default=text("STRFTIME('%Y-%m-%d %H:%M:%f', 'now')")
    )
    __abstract__ = True
    