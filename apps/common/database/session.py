from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from loguru import logger as log
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from apps.common.core.config import DB_URL_SQLALCHEMY
from apps.common.database.model_orm import Base


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """
    Настраивает SQLite для работы в асинхронном режиме.

    Включает поддержку внешних ключей, режим WAL (Write-Ahead Logging)
    для конкурентности и устанавливает таймаут ожидания блокировки.

    Args:
        dbapi_connection: Объект соединения DBAPI.
        connection_record: Запись соединения.
    """
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.execute("PRAGMA journal_mode = WAL")
        cursor.execute("PRAGMA busy_timeout = 5000")
        cursor.close()
        log.debug("SQLitePragma | status=configured foreign_keys=ON journal_mode=WAL busy_timeout=5000")
    except SQLAlchemyError:
        log.exception("SQLitePragma | status=failed reason='Error configuring SQLite PRAGMA'")


async_engine = create_async_engine(
    DB_URL_SQLALCHEMY,
    echo=False,
)

async_session_factory = async_sessionmaker(
    bind=async_engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Предоставляет асинхронный контекстный менеджер для управления сессией SQLAlchemy.

    Гарантирует корректное открытие, коммит, откат и закрытие сессии.

    Yields:
        Экземпляр `AsyncSession`.

    Raises:
        SQLAlchemyError: Если произошла ошибка SQLAlchemy во время транзакции.
        Exception: Для любых других неожиданных ошибок.
    """
    session: AsyncSession = async_session_factory()
    try:
        yield session
        await session.commit()
        log.debug("SQLAlchemySession | event=commit status=success")
    except SQLAlchemyError:
        log.exception("SQLAlchemySession | event=rollback status=failed reason='SQLAlchemy error'")
        await session.rollback()
        raise
    except Exception:
        log.exception("SQLAlchemySession | event=rollback status=failed reason='Unexpected error'")
        await session.rollback()
        raise
    finally:
        await session.close()
        log.debug("SQLAlchemySession | event=close status=success")


async def create_db_tables() -> None:
    """
    Создает все таблицы в базе данных, определенные в `Base.metadata`.

    Если таблицы уже существуют, они не будут пересозданы.

    Raises:
        SQLAlchemyError: Если произошла ошибка SQLAlchemy при создании таблиц.
        Exception: Для любых других неожиданных ошибок.
    """
    log.info("DatabaseTables | event=create_tables_check")
    try:
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        log.info("DatabaseTables | status=success message='Tables created or already exist'")
    except SQLAlchemyError:
        log.exception("DatabaseTables | status=failed reason='SQLAlchemy error during table creation'")
        raise
    except Exception:
        log.exception("DatabaseTables | status=failed reason='Unexpected error during table creation'")
        raise
