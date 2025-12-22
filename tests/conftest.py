import asyncio
from contextlib import suppress

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apps.common.core.container import AppContainer
from apps.common.core.settings import settings

TEST_DB_URL = settings.sqlalchemy_database_url


# 1. Event Loop - scope="function" для полной изоляции
@pytest.fixture(scope="function")
def event_loop():
    """
    Создает экземпляр цикла событий для каждого теста.
    """
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# 2. БД (SQLAlchemy) - scope="function"
@pytest.fixture(scope="function")
async def async_db_engine():
    """
    Создает движок БД для каждого теста.
    """
    engine = create_async_engine(TEST_DB_URL, echo=False)
    yield engine
    await engine.dispose()


# 3. Фабрика сессий
@pytest.fixture(scope="function")
def async_session_factory(async_db_engine):
    return async_sessionmaker(bind=async_db_engine, class_=AsyncSession, expire_on_commit=False)


# 4. Сессия для теста
@pytest.fixture(scope="function")
async def get_async_session(async_session_factory):
    """
    Предоставляет фабрику сессий.
    """
    return async_session_factory


# 5. Контейнер зависимостей - scope="function"
@pytest.fixture(scope="function")
async def app_container():
    """
    Создает и предоставляет экземпляр AppContainer для каждого теста.
    """
    container = AppContainer()
    yield container
    with suppress(RuntimeError):
        await container.shutdown()
