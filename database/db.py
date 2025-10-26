# В твоем файле db.py
import logging
import aiosqlite

from contextlib import asynccontextmanager
from app.core.config import DB_NAME

log = logging.getLogger(__name__)


@asynccontextmanager
async def get_db_connection():
    """
    "Функция-активатор".
    Открывает -> Настраивает -> Отдает -> (Управляет Транзакцией) -> Закрывает.
    """
    db = None
    try:
        # 1. Подключаемся
        db = await aiosqlite.connect(DB_NAME)
        log.info("БД успешно открыта")

        # 2. Настраиваем Row Factory
        db.row_factory = aiosqlite.Row
        log.info("БД успешно настроена")

        # 3. АКТИВИРУЕМ FOREIGN KEYS
        await db.execute("PRAGMA foreign_keys = ON;")
        log.info("БД успешно активирована")

        # 4. "Отдаем" настроенное соединение в блок 'async with'
        yield db

        # 5. завершился БЕЗ ОШИБОК, мы коммитим транзакцию.
        await db.commit()
        log.info("Транзакция успешно ЗАКОММИЧЕНА")

    except aiosqlite.Error as e:
        log.error(f"Ошибка при работе с БД: {e}")
        if db:
            # 6. Если в блоке 'yield' (в хэндлере) произошла ошибка,
            # мы откатываем все изменения.
            await db.rollback()
            log.warning("Транзакция ОТКАЧЕНА")
        # Пробрасываем ошибку дальше, чтобы aiogram ее поймал
        raise

    finally:
        # 7. Гарантированно закрываем соединение
        if db:
            await db.close()
            log.info("БД успешно закрыта")