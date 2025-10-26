# database/schema.py
import aiosqlite
import logging
from pathlib import Path


log = logging.getLogger(__name__)

SQL_DIR_PATH = Path("database/sql")


async def init_database(db: aiosqlite.Connection):
    log.info("Инициализация базы данных...")
    try:
        log.info(f"Ищем .sql файлы в {SQL_DIR_PATH}")
        sql_files = sorted(list(SQL_DIR_PATH.glob("*.sql")))

        if not sql_files:
            log.warning(f"В папке {SQL_DIR_PATH} не найдено .sql файлов!")
            return

        log.info(f"Найдено {len(sql_files)} файлов. Выполняем...")

        for sql_file in sql_files:
            log.debug(f"Выполняем файл: {sql_file.name}")
            sql_script = sql_file.read_text(encoding="utf-8")
            await db.executescript(sql_script)

        await db.commit()
        log.info("База данных успешно инициализирована.")
    except Exception as e:
        log.error(f"Ошибка при инициализации базы данных: {e}")
        await db.rollback()





