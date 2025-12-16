import asyncio

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apps.common.core.container import AppContainer
from apps.common.core.settings import settings

TEST_DB_URL = settings.sqlalchemy_database_url


# 1. Принудительно задаем Scope сессии для Event Loop
@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
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
    try:
        # Пытаемся закрыть соединения корректно
        await container.shutdown()
    except RuntimeError as e:
        # Если Windows уже закрыл цикл событий раньше времени, просто игнорируем это
        if "Event loop is closed" not in str(e):
            raise e
