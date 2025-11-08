# 1. Импортируем 'datetime' из стандартной библиотеки
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.orm import (
    declarative_base,
    Mapped,
    mapped_column
)
from sqlalchemy.types import TIMESTAMP

# Создание декларативной базы.
Base = declarative_base()


class TimestampMixin:
    """
    Миксин (примесь) для добавления полей временных меток в модели.

    Этот класс добавляет два поля: `created_at` и `updated_at`, которые
    автоматически управляются базой данных на уровне сервера (в UTC).

    Attributes:
        # 2. Тип в Python - 'datetime'
        created_at (Mapped[datetime]): Время создания записи (UTC).
            Устанавливается базой данных при вставке новой строки.
        # 3. Тип в Python - 'datetime'
        updated_at (Mapped[datetime]): Время последнего обновления записи (UTC).
            Обновляется триггерами БД при изменении строки.
    """
    __abstract__ = True

    # 2. Меняем Mapped[str] на Mapped[datetime]
    created_at: Mapped[datetime] = mapped_column(
        # 3. Оставляем ваш SQLite-специфичный server_default
        server_default=text("STRFTIME('%Y-%m-%d %H:%M:%S', 'now')"),
        nullable=False
    )

    # 4. Меняем Mapped[str] на Mapped[datetime]
    updated_at: Mapped[datetime] = mapped_column(
        # 5. Оставляем ваш SQLite-специфичный server_default
        server_default=text("STRFTIME('%Y-%m-%d %H:%M:%S', 'now')"),
        nullable=False
        # P.S. 'onupdate' здесь не нужен, так как вы
        # (судя по docstring) используете внешние триггеры.
    )