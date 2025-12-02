# database/session.py
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

from app.core.config import DB_URL_SQLALCHEMY
from database.model_orm import Base


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """
    Настройка SQLite для работы в асинхронном режиме.
    Включает Foreign Keys и режим WAL (Write-Ahead Logging) для конкурентности.
    """
    cursor = dbapi_connection.cursor()
    try:
        # 1. Включаем поддержку внешних ключей
        cursor.execute("PRAGMA foreign_keys = ON")

        # 2. 🔥 Включаем WAL-режим (Решает проблему database is locked)
        cursor.execute("PRAGMA journal_mode = WAL")

        # 3. Устанавливаем таймаут ожидания блокировки (на всякий случай)
        cursor.execute("PRAGMA busy_timeout = 5000")

        cursor.close()
        log.debug("SQLite PRAGMA: FK=ON, Journal=WAL, Timeout=5000.")
    except SQLAlchemyError as e:
        log.error(f"Не удалось настроить SQLite PRAGMA: {e}")


# Создание асинхронного "движка"
async_engine = create_async_engine(
    DB_URL_SQLALCHEMY,
    echo=False,
)

# Создание фабрики сессий
async_session_factory = async_sessionmaker(
    bind=async_engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Асинхронный контекстный менеджер для управления сессией SQLAlchemy.
    """
    # log.debug("Запрос на получение новой сессии SQLAlchemy...")
    session: AsyncSession = async_session_factory()
    try:
        yield session
        await session.commit()
        # log.debug("Транзакция SQLAlchemy успешно закоммичена.")
    except SQLAlchemyError as e:
        log.error(f"Ошибка в сессии SQLAlchemy: {e}. Выполняется откат.")
        await session.rollback()
        raise
    except Exception as e:
        log.error(f"Неожиданная ошибка в блоке сессии: {e}. Выполняется откат.")
        await session.rollback()
        raise
    finally:
        await session.close()


async def create_db_tables() -> None:
    """Создает все таблицы в базе данных."""
    log.info("Проверка и создание таблиц БД...")
    try:
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        log.info("Таблицы успешно созданы (или уже существуют).")
    except SQLAlchemyError as e:
        log.exception(f"Критическая ошибка SQLAlchemy при создании таблиц: {e}")
        raise
    except Exception as e:
        log.exception(f"Критическая ошибка при создании таблиц: {e}")
        raise
