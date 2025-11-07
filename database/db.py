# database/db.py
import logging
import aiosqlite
from contextlib import asynccontextmanager

from app.core.config import DB_NAME

log = logging.getLogger(__name__)


@asynccontextmanager
async def get_db_connection():
    """
    Асинхронный контекстный менеджер для управления подключением к SQLite.

    Эта функция-генератор выполняет полный цикл работы с базой данных:
    1. Открывает соединение.
    2. Настраивает `row_factory` для удобного доступа к данным.
    3. Включает поддержку внешних ключей (foreign keys).
    4. Передает управление (yield) коду внутри блока `async with`.
    5. Если блок завершается без ошибок, коммитит транзакцию.
    6. Если в блоке происходит исключение, откатывает транзакцию.
    7. Гарантированно закрывает соединение в любом случае.

    Yields:
        aiosqlite.Connection: Настроенный объект подключения к базе данных.

    Raises:
        aiosqlite.Error: Пробрасывает исключения, связанные с работой БД,
                         после отката транзакции.
    """
    db: Optional[aiosqlite.Connection] = None
    try:
        # Шаг 1: Подключение к файлу базы данных.
        db = await aiosqlite.connect(DB_NAME)
        log.debug(f"Соединение с базой данных '{DB_NAME}' установлено.")

        # Шаг 2: Настройка row_factory для получения результатов в виде
        # объектов, похожих на dict.
        db.row_factory = aiosqlite.Row
        log.debug("Row factory для соединения установлен на aiosqlite.Row.")

        # Шаг 3: Активация поддержки внешних ключей для обеспечения целостности данных.
        await db.execute("PRAGMA foreign_keys = ON;")
        log.debug("PRAGMA foreign_keys = ON выполнена.")

        # Шаг 4: Передача управления в блок 'async with'.
        # С этого момента и до конца блока все SQL-операции выполняются
        # в рамках одной транзакции.
        yield db

        # Шаг 5: Если код в блоке 'with' завершился без ошибок,
        # фиксируем все изменения.
        await db.commit()
        log.debug("Транзакция успешно закоммичена.")

    except aiosqlite.Error as e:
        # Шаг 6: Если в блоке 'with' или при коммите произошла ошибка,
        # откатываем все изменения, сделанные в рамках этой транзакции.
        log.error(f"Ошибка при работе с БД: {e}. Выполняется откат транзакции.")
        if db:
            await db.rollback()
            log.warning("Транзакция была откатана.")
        # Пробрасываем исключение дальше, чтобы оно было обработано
        # на более высоком уровне.
        raise

    finally:
        # Шаг 7: Гарантированное закрытие соединения, независимо от того,
        # была ошибка или нет.
        if db:
            await db.close()
            log.debug(f"Соединение с базой данных '{DB_NAME}' закрыто.")
