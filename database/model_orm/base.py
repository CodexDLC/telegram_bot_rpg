# database/model_orm/base.py
from sqlalchemy import text
from sqlalchemy.orm import (
    declarative_base,
    Mapped,
    mapped_column
)
from sqlalchemy.types import TIMESTAMP

# Создание декларативной базы.
# Все ORM-модели должны наследоваться от этого класса.
Base = declarative_base()


class TimestampMixin:
    """
    Миксин (примесь) для добавления полей временных меток в модели.

    Этот класс добавляет два поля: `created_at` и `updated_at`, которые
    автоматически управляются базой данных на уровне сервера.

    Attributes:
        created_at (Mapped[str]): Время создания записи.
            Устанавливается базой данных при вставке новой строки.
        updated_at (Mapped[str]): Время последнего обновления записи.
            Устанавливается базой данных при вставке и может быть
            обновлено триггерами при изменении строки.
    """
    __abstract__ = True  # Указывает SQLAlchemy, что это не модель для маппинга.

    # server_default использует функцию БД для установки значения.
    # STRFTIME - специфична для SQLite. Для PostgreSQL нужно использовать NOW().
    # Использование TIMESTAMP с timezone=True рекомендуется для кросс-совместимости.
    created_at: Mapped[str] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("TIMEZONE('utc', now())"),
        nullable=False
    )
    updated_at: Mapped[str] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("TIMEZONE('utc', now())"),
        onupdate=text("TIMEZONE('utc', now())"),
        nullable=False
    )
