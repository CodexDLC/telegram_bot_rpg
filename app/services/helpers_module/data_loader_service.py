# app/services/helpers_module/data_loader_service.py
import asyncio
from loguru import logger as log
from typing import List, Dict, Any, Callable, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from database.repositories.ORM.characters_repo_orm import CharactersRepoORM, CharacterStatsRepoORM
from database.repositories.ORM.skill_repo import SkillProgressRepo
from database.repositories.ORM.users_repo_orm import UsersRepoORM
from database.session import get_async_session


# Карта загрузчиков данных.
# Ключ - строка, которую мы используем в `include`.
# Значение - кортеж из (фабрика_репозитория, имя_метода_в_репозитории).
DATA_LOADERS_MAP: Dict[str, Tuple[Callable[[AsyncSession], Any], str]] = {
    "user": (UsersRepoORM, "get_user"),
    "character": (CharactersRepoORM, "get_character"),
    "characters": (CharactersRepoORM, "get_characters"),
    "character_stats": (CharacterStatsRepoORM, "get_stats"),
    "character_progress": (SkillProgressRepo, "get_all_skills_progress"),
}
log.debug(f"Карта DATA_LOADERS_MAP инициализирована с {len(DATA_LOADERS_MAP)} загрузчиками.")


async def load_data_auto(include: List[str], **kwargs: Any) -> Dict[str, Any]:
    """
    Асинхронно загружает различные наборы данных из базы данных.

    Эта функция динамически вызывает методы репозиториев на основе списка `include`.
    Она открывает одну сессию SQLAlchemy и выполняет все запросы параллельно
    с помощью `asyncio.gather`.

    Пример использования:
        `data = await load_data_auto(include=["character", "character_stats"], char_id=123)`
        `character_dto = data.get("character")`

    Args:
        include (List[str]): Список ключей, указывающих, какие данные нужно
                             загрузить (см. `DATA_LOADERS_MAP`).
        **kwargs: Аргументы (например, `char_id`, `user_id`), которые будут
                  переданы в методы репозиториев.

    Returns:
        Dict[str, Any]: Словарь, где ключи - это строки из `include`,
                        а значения - результаты выполнения соответствующих
                        методов репозиториев.
    """
    if not include:
        log.warning("'load_data_auto' вызван с пустым списком 'include'.")
        return {}

    log.info(f"Запрос на асинхронную загрузку данных: {include} с параметрами: {kwargs}")
    results: Dict[str, Any] = {}

    async with get_async_session() as session:
        tasks = []
        for key in include:
            if key not in DATA_LOADERS_MAP:
                log.warning(f"Ключ '{key}' не найден в DATA_LOADERS_MAP и будет проигнорирован.")
                continue

            repo_factory, method_name = DATA_LOADERS_MAP[key]
            repo = repo_factory(session)
            method = getattr(repo, method_name)

            # Создаем корутину для выполнения метода репозитория.
            # `kwargs` передаются в метод, что позволяет гибко фильтровать данные.
            task = asyncio.create_task(method(**kwargs), name=f"load_{key}")
            tasks.append((key, task))

        log.debug(f"Создано {len(tasks)} задач для параллельной загрузки данных.")
        # Ожидаем завершения всех задач.
        task_results = await asyncio.gather(*[t for _, t in tasks])

        # Собираем результаты в словарь.
        for (key, _), result_value in zip(tasks, task_results):
            results[key] = result_value

    log.info(f"Загрузка данных завершена. Получены ключи: {list(results.keys())}")
    log.debug(f"Полные результаты загрузки: {results}")
    return results
