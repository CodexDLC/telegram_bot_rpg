from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from loguru import logger as log
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
database_url = settings.sqlalchemy_database_url

# --- 2. Настраиваем аргументы для Postgres ---
connect_args: dict[str, Any] = {
    "prepared_statement_cache_size": 0,
}
if settings.db_ssl_require:
    connect_args["ssl"] = "require"

pool_settings: dict[str, Any] = {
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

# --- 4. Фабрика и Сессия ---
async_session_factory = async_sessionmaker(
    bind=async_engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Предоставляет сессию с автоматическим управлением транзакцией.
    При успешном завершении блока - commit.
    При ошибке - rollback.
    """
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
