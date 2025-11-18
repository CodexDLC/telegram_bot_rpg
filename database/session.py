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
    Включает поддержку FOREIGN KEY (и ON DELETE CASCADE)
    при каждом новом подключении к SQLite.
    """
    # Этот код будет синхронным, так как SQLAlchemy
    # обрабатывает низкоуровневые коннекты в `greenlet`
    try:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")
        cursor.close()
        log.debug("PRAGMA foreign_keys=ON включен для нового соединения.")
    except SQLAlchemyError as e:
        log.error(f"Не удалось включить PRAGMA foreign_keys: {e}")


# Создание асинхронного "движка" для подключения к базе данных.
# Движок - это фабрика соединений, управляющая пулом подключений.
# echo=True выводит все SQL-запросы, генерируемые SQLAlchemy, в логи.
# Это полезно для отладки, но в продакшене лучше установить в False.
async_engine = create_async_engine(
    DB_URL_SQLALCHEMY,
    echo=False,  # В продакшене рекомендуется отключать
)

# Создание фабрики сессий.
# Фабрика конфигурирует, как должны создаваться новые сессии.
# expire_on_commit=False предотвращает истечение срока действия объектов
# после коммита, что позволяет использовать их дальше (например, в сериализаторах).
async_session_factory = async_sessionmaker(
    bind=async_engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Асинхронный контекстный менеджер для управления сессией SQLAlchemy.

    Предоставляет сессию для работы с базой данных и автоматически управляет
    жизненным циклом транзакции: коммитит при успехе, откатывает при ошибке
    и всегда закрывает сессию.

    Yields:
        AsyncSession: Объект асинхронной сессии для выполнения операций с БД.

    Raises:
        SQLAlchemyError: Пробрасывает исключения, связанные с работой БД,
                         после отката транзакции.
    """
    log.debug("Запрос на получение новой сессии SQLAlchemy...")
    session: AsyncSession = async_session_factory()
    try:
        # Передаем управление в блок 'async with', предоставляя сессию.
        yield session
        # Если блок завершился без ошибок, коммитим транзакцию.
        await session.commit()
        log.debug("Транзакция SQLAlchemy успешно закоммичена.")
    except SQLAlchemyError as e:
        # При возникновении любой ошибки SQLAlchemy откатываем транзакцию.
        log.error(f"Ошибка в сессии SQLAlchemy: {e}. Выполняется откат.")
        await session.rollback()
        log.warning("Транзакция SQLAlchemy была откатана.")
        raise
    except Exception as e:
        # Ловим и другие возможные ошибки, не связанные с SQLAlchemy.
        log.error(f"Неожиданная ошибка в блоке сессии: {e}. Выполняется откат.")
        await session.rollback()
        log.warning("Транзакция SQLAlchemy была откатана из-за неожиданной ошибки.")
        raise
    finally:
        # Гарантированно закрываем сессию.
        await session.close()
        log.debug("Сессия SQLAlchemy закрыта.")


async def create_db_tables() -> None:
    """
    Создает все таблицы в базе данных на основе метаданных ORM-моделей.

    Эта функция использует `Base.metadata.create_all`, чтобы создать таблицы
    для всех моделей, унаследованных от декларативной базы `Base`.
    Это простой способ инициализации схемы, который не поддерживает миграции.

    Returns:
        None
    """
    log.info("Проверка и создание таблиц БД на основе моделей SQLAlchemy...")
    try:
        async with async_engine.begin() as conn:
            # run_sync выполняет синхронную функцию create_all в асинхронном окружении.
            await conn.run_sync(Base.metadata.create_all)
        log.info("Проверка и создание таблиц успешно завершено.")
    except Exception as e:
        log.exception(f"Критическая ошибка при создании таблиц в базе данных: {e}")
        raise
