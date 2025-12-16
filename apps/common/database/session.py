from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from loguru import logger as log
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Импортируем наш обновленный объект настроек
from apps.common.core.settings import settings
from apps.common.database.model_orm import Base

# --- 1. Получаем URL из настроек ---
# settings.sqlalchemy_database_url уже содержит правильный префикс (postgresql+asyncpg://)
database_url = settings.sqlalchemy_database_url

# Определяем тип базы для аргументов
is_sqlite = "sqlite" in database_url

# --- 2. Настраиваем аргументы ---
connect_args: dict[str, Any] = {}
pool_settings: dict[str, Any] = {}

if is_sqlite:
    connect_args = {"check_same_thread": False}
else:
    # Postgres (Neon)
    connect_args = {"ssl": "require"}
    pool_settings = {
        "pool_size": 20,
        "max_overflow": 10,
    }

# --- 3. Создаем движок ---
async_engine = create_async_engine(
    database_url,
    echo=False,
    connect_args=connect_args,
    **pool_settings,
)

# --- 4. SQLite Fix (только если SQLite) ---
if is_sqlite:

    @event.listens_for(Engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.execute("PRAGMA journal_mode = WAL")
            cursor.execute("PRAGMA busy_timeout = 5000")
            cursor.close()
        except SQLAlchemyError:
            log.exception("SQLitePragma | status=failed")


# --- 5. Фабрика и Сессия (как было) ---
async_session_factory = async_sessionmaker(
    bind=async_engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    session: AsyncSession = async_session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def create_db_tables() -> None:
    """Создает таблицы (если не используешь Alembic)"""
    try:
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        log.info("Tables created successfully")
    except SQLAlchemyError as e:
        log.error(f"Error creating tables: {e}")
