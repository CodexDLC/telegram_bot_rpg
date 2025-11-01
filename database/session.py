# database/session.py

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)

from app.core.config import DB_URL_SQLALCHEMY
from database.model_orm import Base

log = logging.getLogger(__name__)

async_engine = create_async_engine(
    DB_URL_SQLALCHEMY,
    echo=True)

async_session_factory = async_sessionmaker(
    bind=async_engine,
    expire_on_commit=False,
    class_=AsyncSession,

)

@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
        "Функция-активатор" для SQLAlchemy.
        Открывает -> Отдает сессию -> (Управляет Транзакцией) -> Закрывает.
    """

    log.debug("Выдача асинхронной сессии SQLAlchemy")
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
            log.debug("Транзакция SQLAlchemy ЗАКОММИЧЕНА")
        except Exception as e:
            log.error(f"Ошибка в сессии SQLAlchemy: {e}")
            await session.rollback()
            log.warning("Транзакция SQLAlchemy ОТКАЧЕНА")
            raise
        finally:
            log.debug("Сессия SQLAlchemy закрыта")

async def create_db_tables():
    """
    Создает таблицы в БД на основе ORM-моделей.
    "Способ А" - простой (без миграций).
    """
    log.info("Создание таблиц БД (если их нет)...")
    async with async_engine.begin() as conn:
        # Эта команда "смотрит" на все классы,
        # унаследованные от Base, и создает их
        await conn.run_sync(Base.metadata.create_all)
    log.info("Создание таблиц завершено.")