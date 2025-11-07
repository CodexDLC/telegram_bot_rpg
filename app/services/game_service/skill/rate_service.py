# app/services/game_service/skill/rate_service.py
import logging
from typing import Dict, List, Any

from app.resources.game_data.skill_library import SKILL_RECIPES
from app.resources.schemas_dto.character_dto import CharacterStatsReadDTO

log = logging.getLogger(__name__)


def calculate_rates_data(
    character_id: int,
    stats_dto: CharacterStatsReadDTO
) -> List[Dict[str, Any]]:
    """
    Рассчитывает "Базовую Ставку Опыта" (БСО) для всех навыков.

    Эта функция-хелпер проходит по всем навыкам, определенным в `SKILL_RECIPES`,
    и для каждого из них вычисляет БСО на основе первичных и вторичных
    характеристик персонажа.

    Формула расчета: `(значение_главной_характеристики * 2) + (значение_второстепенной * 1)`

    Args:
        character_id (int): ID персонажа, для которого производится расчет.
        stats_dto (CharacterStatsReadDTO): DTO с характеристиками персонажа.

    Returns:
        List[Dict[str, Any]]: Список словарей, готовых для массовой вставки
                               (UPSERT) в базу данных через репозиторий.
                               Каждый словарь содержит `character_id`,
                               `skill_key` и рассчитанный `xp_per_tick`.
    """
    log.debug(f"Начало расчета БСО для character_id={character_id} на основе статов: {stats_dto.model_dump_json()}")

    rates_to_upsert: List[Dict[str, Any]] = []

    for skill_key, recipe in SKILL_RECIPES.items():
        primary_stat_name = recipe.get("primary")
        secondary_stat_name = recipe.get("secondary")

        if not primary_stat_name or not secondary_stat_name:
            log.warning(f"Для навыка '{skill_key}' не определены primary или secondary характеристики в SKILL_RECIPES.")
            continue

        # Безопасно получаем значения характеристик из DTO.
        # Если характеристика не найдена, используется значение по умолчанию 0.
        primary_val = getattr(stats_dto, primary_stat_name, 0)
        secondary_val = getattr(stats_dto, secondary_stat_name, 0)

        # Формула расчета ставки.
        xp_tick_rate = (primary_val * 2) + (secondary_val * 1)
        log.debug(f"  - Навык: {skill_key}, Первичная: {primary_stat_name}({primary_val}), Вторичная: {secondary_stat_name}({secondary_val}) -> БСО: {xp_tick_rate}")

        rates_to_upsert.append({
            "character_id": character_id,
            "skill_key": skill_key,
            "xp_per_tick": xp_tick_rate
        })

    log.info(f"Для character_id={character_id} рассчитано {len(rates_to_upsert)} ставок БСО.")
    return rates_to_upsert
