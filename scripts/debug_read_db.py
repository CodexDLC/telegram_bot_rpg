import asyncio
import json
import os
import sys
from contextlib import suppress

# --- Настройка окружения ---
# Этот блок должен выполняться ДО импорта любых модулей проекта,
# так как они могут зависеть от текущей рабочей директории при инициализации.
current_dir = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(current_dir)
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

# --- Импорты ---
# Теперь, когда рабочая директория установлена на корень проекта,
# можно безопасно импортировать модули.
from loguru import logger as log  # noqa: E402
from sqlalchemy import exc, text  # noqa: E402

from database.session import async_session_factory  # noqa: E402


async def read_region_data():
    """
    Подключается к БД и выводит все данные из таблицы world_regions
    в формате JSON-строк.
    """
    log.info("Запускаем скрипт для чтения данных из таблицы 'world_regions'...")

    query = text("""
        SELECT *
        FROM world_regions;
    """)

    async with async_session_factory() as session:
        try:
            log.info("Сессия с БД открыта. Выполняем запрос к таблице 'world_regions'...")

            result = await session.execute(query)
            rows = result.fetchall()

            if not rows:
                log.warning("Данные в таблице 'world_regions' не найдены.")
                return

            keys = list(result.keys())

            log.info(f"--- НАЙДЕНО {len(rows)} ЗАПИСЕЙ В ТАБЛИЦЕ 'world_regions' ---")
            for row in rows:
                row_data = {}
                for i, value in enumerate(row):
                    key_name = keys[i]
                    cell_value = value

                    # Попытка декодировать JSON-строки для лучшей читаемости
                    if isinstance(value, str):
                        with suppress(json.JSONDecodeError):
                            cell_value = json.loads(value)
                    row_data[key_name] = cell_value

                # Выводим каждую строку как JSON-объект
                print(json.dumps(row_data, ensure_ascii=False, indent=2))
            log.info("-------------------------------------------------")

        except exc.SQLAlchemyError as e:
            log.exception(f"Произошла ошибка при чтении из БД: {e}")
        finally:
            log.info("Скрипт завершил работу.")


if __name__ == "__main__":
    # Устанавливаем корневую директорию проекта как текущую рабочую директорию
    # для корректного разрешения относительных путей (например, к БД).
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)
    asyncio.run(read_region_data())
