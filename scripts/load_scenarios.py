import asyncio
import sys
from pathlib import Path

# Добавляем корень проекта в sys.path, чтобы видеть пакеты apps
sys.path.append(str(Path(__file__).parent.parent))

# ВАЖНО: Импортируем модели, чтобы они зарегистрировались в Base.metadata перед созданием таблиц
from apps.common.database import create_db_tables, get_async_session
from loguru import logger as log
from sqlalchemy import text

from backend.domains.user_features.scenario.resources.loaders.scenario_loader import ScenarioLoader


async def recreate_scenario_tables():
    """
    Удаляет и создает заново таблицы сценариев.
    Нужно для применения изменений схемы (например, добавления UniqueConstraint).
    """
    async with get_async_session() as session:
        log.warning("Dropping scenario tables to apply schema changes...")
        # Удаляем таблицы в правильном порядке (из-за Foreign Keys)
        await session.execute(text("DROP TABLE IF EXISTS character_scenario_state CASCADE"))
        await session.execute(text("DROP TABLE IF EXISTS scenario_nodes CASCADE"))
        await session.execute(text("DROP TABLE IF EXISTS scenario_master CASCADE"))
        await session.commit()
        log.info("Scenario tables dropped.")

    # Создаем таблицы заново через SQLAlchemy
    await create_db_tables()


async def main():
    """
    Скрипт для загрузки/обновления сценариев из JSON в БД.
    """
    log.info("Starting scenario loader...")

    # 1. Пересоздаем таблицы (чтобы применились индексы и новые поля)
    await recreate_scenario_tables()

    # 2. Загружаем данные
    async with get_async_session() as session:
        loader = ScenarioLoader(session)
        await loader.load_all_scenarios()

    log.info("Scenario loading completed.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.warning("Loader interrupted by user.")
    except Exception as e:  # noqa: BLE001
        log.exception(f"Loader failed with error: {e}")
        sys.exit(1)
