# app/services/data_loader_service.py
import asyncio

from database.db import get_db_connection
from database.repositories import (
    get_user_repo,
    get_character_repo,
    get_character_stats_repo
)

DATA_LOADERS_MAP = {

    "user" : (get_user_repo, "get_user"),
    "character": (get_character_repo, "get_character"),
    "characters" : (get_character_repo, "get_characters"),
    "character_stats" : (get_character_stats_repo, "get_stats")

}


async def load_data_auto(
        include: list[str] = None,
        **kw
        )-> dict:


    if include is None:
        return {}

    results = {}

    async with get_db_connection() as db:
        tasks = []
        for key in include:
            if key not in DATA_LOADERS_MAP:
                continue

            get_repo_func, method_name = DATA_LOADERS_MAP[key]
            repo = get_repo_func(db)
            method = getattr(repo, method_name)

            async def run_method(k=key, m=method):
                try:
                    return k, await m(**kw)
                except TypeError:
                    return k, await m()

            tasks.append(run_method())

        done = await asyncio.gather(*tasks)
        results = dict(done)

    return results