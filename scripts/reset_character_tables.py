import asyncio
import sys
from pathlib import Path

# Добавляем корень проекта в sys.path
sys.path.append(str(Path(__file__).parent.parent))

from loguru import logger as log
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

# Импортируем модели, чтобы они были в metadata
from apps.common.database.model_orm import *  # noqa: F403
from apps.common.database.session import create_db_tables, get_async_session


async def reset_character_tables():
    """
    Сбрасывает таблицы, связанные с персонажем, для применения миграций схемы.
    Не трогает таблицы мира и пользователей (если возможно).
    """
    async with get_async_session() as session:
        log.warning("Dropping character-related tables...")

        # Порядок важен из-за Foreign Keys!
        # Сначала удаляем зависимые таблицы
        tables_to_drop = [
            "character_scenario_state",
            "character_stats",
            "character_skill_progress",
            "character_skill_rate",
            "character_symbiote",
            "inventory_items",
            "resource_wallets",
            "leaderboard",
            # "characters" удаляем последним из зависимых
            "characters",
        ]

        for table in tables_to_drop:
            try:
                # Используем CASCADE, чтобы удалить и связи
                await session.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
                log.info(f"Dropped table: {table}")
            except SQLAlchemyError as e:
                log.error(f"Failed to drop {table}: {e}")
            except Exception as e:  # noqa: BLE001
                log.error(f"Unexpected error dropping {table}: {e}")

        await session.commit()
        log.success("Character tables dropped.")

    # Создаем таблицы заново
    # create_db_tables создаст только те, которых нет
    log.info("Recreating tables...")
    await create_db_tables()
    log.success("Tables recreated.")


if __name__ == "__main__":
    try:
        asyncio.run(reset_character_tables())
    except KeyboardInterrupt:
        log.warning("Interrupted by user.")
    except Exception as e:  # noqa: BLE001
        log.exception(f"Failed with error: {e}")
        sys.exit(1)
