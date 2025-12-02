# tests/conftest.py
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import DB_URL_SQLALCHEMY

# Используем ту же БД, что и в конфиге (или можно подменить на test.db)
TEST_DB_URL = DB_URL_SQLALCHEMY


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    import asyncio

    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def async_db_engine():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    yield engine
    await engine.dispose()


@pytest.fixture
async def get_async_session(async_db_engine):
    """
    Фабрика сессий для тестов.
    """
    async_session = async_sessionmaker(bind=async_db_engine, class_=AsyncSession, expire_on_commit=False)

    # Возвращаем фабрику (чтобы можно было делать async with get_async_session())
    return async_session
