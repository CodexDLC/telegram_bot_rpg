from typing import Any

from loguru import logger as log

from app.resources.game_data.skill_library import SKILL_RECIPES
from app.resources.schemas_dto.character_dto import CharacterStatsReadDTO


def calculate_rates_data(character_id: int, stats_dto: CharacterStatsReadDTO) -> list[dict[str, Any]]:
    """
    Рассчитывает "Базовую Ставку Опыта" (БСО) для всех навыков персонажа.

    Для каждого навыка, определенного в `SKILL_RECIPES`, вычисляет БСО
    на основе первичных характеристик персонажа. Формула расчета:
    `(значение_главной_характеристики * 2) + (значение_второстепенной * 1)`.

    Args:
        character_id: Идентификатор персонажа, для которого производится расчет.
        stats_dto: DTO с характеристиками персонажа.

    Returns:
        Список словарей, готовых для массовой вставки (UPSERT) в базу данных.
        Каждый словарь содержит `character_id`, `skill_key` и рассчитанный `xp_per_tick`.
    """
    log.debug(f"SkillRate | event=calculate_rates character_id={character_id}")

    rates_to_upsert: list[dict[str, Any]] = []

    for skill_key, recipe in SKILL_RECIPES.items():
        if not isinstance(recipe, dict):
            continue
        total_xp_tick = 0.0
        stat_weights = recipe.get("stat_weights", {})

        if isinstance(stat_weights, dict):
            for stat_name, multiplier in stat_weights.items():
                stat_value = getattr(stats_dto, stat_name, 0)
                total_xp_tick += stat_value * multiplier

        xp_tick_rate = int(total_xp_tick)
        rates_to_upsert.append({"character_id": character_id, "skill_key": skill_key, "xp_per_tick": xp_tick_rate})

    log.info(f"SkillRate | status=finished calculated_count={len(rates_to_upsert)} character_id={character_id}")
    return rates_to_upsert
