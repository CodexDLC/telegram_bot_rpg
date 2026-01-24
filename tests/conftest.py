from contextlib import suppress

import pytest
from apps.common.core.container import AppContainer
from apps.common.core.settings import settings
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from backend.database.model_orm import Base

TEST_DB_URL = settings.sqlalchemy_test_database_url


# 1. БД (SQLAlchemy) - scope="function"
@pytest.fixture(scope="function")
async def async_db_engine():
    """
    Создает движок БД для каждого теста.
    """
    if "test" not in TEST_DB_URL and ":memory:" not in TEST_DB_URL:
        print(f"WARNING: Running tests on DB: {TEST_DB_URL}")

    # Убрали prepare_threshold, так как он вызывал TypeError
    engine = create_async_engine(TEST_DB_URL, echo=False, poolclass=NullPool)

    # Инициализация БД
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Принудительно закрываем соединения после DDL операций, чтобы сбросить кэши asyncpg
    await engine.dispose()

    yield engine
    await engine.dispose()


# 2. Фабрика сессий
@pytest.fixture(scope="function")
def async_session_factory(async_db_engine):
    return async_sessionmaker(bind=async_db_engine, class_=AsyncSession, expire_on_commit=False)


# 3. Сессия для теста
@pytest.fixture(scope="function")
async def get_async_session(async_session_factory):
    return async_session_factory


# 4. Контейнер зависимостей
@pytest.fixture(scope="function")
async def app_container():
    container = AppContainer()
    yield container
    with suppress(RuntimeError):
        await container.shutdown()
