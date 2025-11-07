# database/schema.py
import aiosqlite
import logging
from pathlib import Path
from typing import List

log = logging.getLogger(__name__)

# Определение пути к директории с SQL-скриптами.
# Использование Path делает код кросс-платформенным.
SQL_DIR_PATH = Path("database/sql")


async def init_database(db: aiosqlite.Connection) -> None:
    """
    Инициализирует схему базы данных, выполняя SQL-скрипты.

    Функция сканирует директорию `database/sql`, находит все `.sql` файлы,
    сортирует их в алфавитном порядке и последовательно выполняет
    содержащиеся в них SQL-команды. Это позволяет создавать или обновлять
    структуру таблиц, индексов и других объектов БД.

    Предполагается, что файлы именуются так, чтобы их алфавитный порядок
    соответствовал порядку их выполнения (например, `01_users.sql`, `02_characters.sql`).

    Args:
        db (aiosqlite.Connection): Активное подключение к базе данных,
                                   в рамках которого будут выполнены скрипты.

    Returns:
        None

    Raises:
        Exception: Пробрасывает исключения, возникшие при выполнении
                   SQL-скриптов, после попытки отката транзакции.
    """
    log.info("Начало инициализации схемы базы данных...")
    try:
        log.debug(f"Поиск SQL-файлов в директории: {SQL_DIR_PATH.resolve()}")
        sql_files: List[Path] = sorted(list(SQL_DIR_PATH.glob("*.sql")))

        if not sql_files:
            log.warning(f"В директории {SQL_DIR_PATH.resolve()} не найдено .sql файлов для инициализации схемы.")
            return

        log.info(f"Найдено {len(sql_files)} SQL-файлов для выполнения.")

        for sql_file in sql_files:
            log.debug(f"Чтение и выполнение скрипта из файла: {sql_file.name}")
            try:
                sql_script = sql_file.read_text(encoding="utf-8")
                # executescript выполняет весь скрипт целиком.
                # Это удобно для создания таблиц и других DDL-операций.
                await db.executescript(sql_script)
                log.debug(f"Скрипт {sql_file.name} успешно выполнен.")
            except Exception as e:
                # Логируем ошибку с указанием конкретного файла
                log.error(f"Ошибка при выполнении скрипта из файла {sql_file.name}: {e}")
                raise  # Прерываем выполнение и переходим к блоку except верхнего уровня

        # Явный commit() здесь не нужен, если init_database вызывается
        # внутри контекстного менеджера get_db_connection, который сам
        # управляет транзакцией. Однако, если функция может вызываться
        # отдельно, commit() обеспечивает применение изменений.
        # Оставим его для надежности.
        await db.commit()
        log.info("Схема базы данных успешно инициализирована.")

    except Exception as e:
        log.error(f"Произошла ошибка в процессе инициализации базы данных: {e}")
        # Попытка откатить транзакцию, если что-то пошло не так.
        await db.rollback()
        log.warning("Выполнена попытка отката изменений в базе данных.")
        # Пробрасываем исключение, чтобы сообщить о сбое вызывающему коду.
        raise
