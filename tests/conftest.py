import asyncio

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import DB_URL_SQLALCHEMY
from app.core.container import AppContainer

TEST_DB_URL = DB_URL_SQLALCHEMY


# 1. Принудительно задаем Scope сессии для Event Loop
@pytest.fixture(scope="session")
def event_loop():
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


# 2. БД (SQLAlchemy)
@pytest.fixture(scope="session")
async def async_db_engine():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    yield engine
    await engine.dispose()


@pytest.fixture
async def get_async_session(async_db_engine):
    async_session = async_sessionmaker(bind=async_db_engine, class_=AsyncSession, expire_on_commit=False)
    return async_session


# 3. Контейнер зависимостей
@pytest.fixture
async def app_container():
    """
    Создает и предоставляет экземпляр AppContainer для тестов.
    Автоматически закрывает соединение с Redis после выполнения теста.
    """
    container = AppContainer()
    yield container
    await container.close()
