import logging
from typing import Dict, List, Any

# Импорт из твоей библиотеки правил
from app.resources.game_data.skill_library import SKILL_RECIPES
from app.resources.schemas_dto.character_dto import CharacterStatsReadDTO

log = logging.getLogger(__name__)


def calculate_rates_data(
    character_id: int,
    stats_dto: CharacterStatsReadDTO
) -> List[Dict[str, Any]]:
    """
    Хелпер-функция.
    Рассчитывает "Базовую Ставку Опыта" (БСО) для ВСЕХ навыков
    и подготавливает список словарей для UPSERT в Репозиторий.
    """
    log.debug(f"Начало расчета БСО для character_id={character_id}")

    rates_to_upsert = []

    for skill_key, recipe in SKILL_RECIPES.items():
        primary_stat_name = recipe.get("primary")
        secondary_stat_name = recipe.get("secondary")

        # Безопасно получаем значения статов из DTO
        primary_val = getattr(stats_dto, primary_stat_name, 0)
        secondary_val = getattr(stats_dto, secondary_stat_name, 0)

        # Формула: (Главный * 2) + (Второстепенный * 1)
        xp_tick_rate = (primary_val * 2) + (secondary_val * 1)

        rates_to_upsert.append({
            "character_id": character_id,
            "skill_key": skill_key,
            "xp_per_tick": xp_tick_rate
        })

    log.debug(f"Рассчитано {len(rates_to_upsert)} БСО.")
    return rates_to_upsert