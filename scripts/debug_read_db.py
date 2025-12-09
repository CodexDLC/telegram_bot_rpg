import asyncio
import json
import os
import sys

from loguru import logger as log
from sqlalchemy import exc, text

from database.session import async_session_factory

# --- Настройка окружения ---
current_dir = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(current_dir)
os.chdir(PROJECT_ROOT)
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)


async def read_arena_node():
    """
    Подключается к БД и выводит все данные для нода "Ангар Арены" (51, 51).
    """
    log.info("Запускаем скрипт для чтения данных 'Ангара Арены' (51, 51)...")

    x_coord, y_coord = 51, 51

    # Запрашиваем ВСЕ колонки (*) для конкретной ячейки
    query = text(f"""
        SELECT *
        FROM world_grid
        WHERE x = {x_coord} AND y = {y_coord};
    """)

    async with async_session_factory() as session:
        try:
            log.info(f"Сессия с БД открыта. Выполняем запрос для координат ({x_coord}, {y_coord})...")

            result = await session.execute(query)
            row = result.fetchone()  # Ожидаем только одну строку

            if not row:
                log.warning(f"В координатах ({x_coord}, {y_coord}) нод не найден.")
                return

            keys = list(result.keys())
            json_column_indices = {i for i, key in enumerate(keys) if key in ["flags", "content"]}

            log.info("--- НАЙДЕНА ЗАПИСЬ ---")
            for i, value in enumerate(row):
                key_name = keys[i]
                cell_value = value

                # Декодируем JSON-строки для читаемости
                if i in json_column_indices and isinstance(value, str):
                    try:
                        data = json.loads(value)
                        cell_value = json.dumps(data, ensure_ascii=False, indent=2)
                    except json.JSONDecodeError:
                        pass

                log.info(f"{key_name}: {cell_value}")
            log.info("----------------------")

        except exc.SQLAlchemyError as e:
            log.exception(f"Произошла ошибка при чтении из БД: {e}")
        finally:
            log.info("Скрипт завершил работу.")


if __name__ == "__main__":
    asyncio.run(read_arena_node())
