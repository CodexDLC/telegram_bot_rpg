import asyncio
import json
import os
import sys
from contextlib import suppress

from loguru import logger as log
from sqlalchemy import exc, text

from apps.common.database.session import async_session_factory

# --- Настройка окружения ---
current_dir = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(current_dir)
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)
os.chdir(PROJECT_ROOT)


# --- Словарь доступных запросов ---
QUERIES = {
    "world_grid": {
        "1": {
            "description": "Показать все АКТИВНЫЕ ячейки (is_active=True)",
            "query": text("SELECT * FROM world_grid WHERE is_active = TRUE;"),
        },
        "2": {
            "description": "Показать ячейки, где НЕ сгенерирован контент (is_active=True, title IS NULL)",
            "query": text(
                "SELECT x, y, is_active, content FROM world_grid WHERE is_active = TRUE AND json_extract(content, '$.title') IS NULL;"
            ),
        },
        "3": {
            "description": "Показать ВООБЩЕ ВСЕ ячейки (ОСТОРОЖНО, LIMIT 100)",
            "query": text("SELECT * FROM world_grid LIMIT 100;"),
        },
    },
    "world_regions": {
        "1": {
            "description": "Показать все регионы",
            "query": text("SELECT * FROM world_regions;"),
        }
    },
}


async def execute_and_print_query(query):
    """Выполняет переданный запрос и красиво печатает результат."""
    async with async_session_factory() as session:
        try:
            result = await session.execute(query)
            rows = result.fetchall()

            if not rows:
                log.warning("Запрос не вернул данных.")
                return

            keys = list(result.keys())
            log.info(f"--- НАЙДЕНО {len(rows)} ЗАПИСЕЙ ---")
            for row in rows:
                row_data = {}
                for i, value in enumerate(row):
                    key_name = keys[i]
                    cell_value = value
                    if isinstance(value, str):
                        with suppress(json.JSONDecodeError):
                            cell_value = json.loads(value)
                    row_data[key_name] = cell_value
                print(json.dumps(row_data, ensure_ascii=False, indent=2))
            log.info("---------------------------------")

        except exc.SQLAlchemyError as e:
            log.exception(f"Произошла ошибка при выполнении запроса: {e}")


async def main():
    """Основной цикл интерактивного меню."""
    log.info("Запуск интерактивного отладчика БД...")

    while True:
        # --- Меню выбора таблицы ---
        print("\n--- Выберите таблицу для анализа ---")
        table_choices = list(QUERIES.keys())
        for i, table_name in enumerate(table_choices):
            print(f"{i + 1}. {table_name}")
        print("0. Выход")

        try:
            table_choice = int(input("Ваш выбор: "))
            if table_choice == 0:
                break
            if not (1 <= table_choice <= len(table_choices)):
                raise ValueError

            selected_table = table_choices[table_choice - 1]

        except (ValueError, IndexError):
            log.error("Некорректный ввод. Попробуйте снова.")
            continue

        # --- Меню выбора запроса ---
        print(f"\n--- Выберите запрос для таблицы '{selected_table}' ---")
        query_map = QUERIES[selected_table]
        for key, value in query_map.items():
            print(f"{key}. {value['description']}")
        print("0. Назад")

        try:
            query_choice = input("Ваш выбор: ")
            if query_choice == "0":
                continue
            if query_choice not in query_map:
                raise ValueError

            selected_query = query_map[query_choice]["query"]
            await execute_and_print_query(selected_query)

        except (ValueError, IndexError):
            log.error("Некорректный ввод. Попробуйте снова.")
            continue

    log.info("Скрипт завершил работу.")


if __name__ == "__main__":
    asyncio.run(main())
