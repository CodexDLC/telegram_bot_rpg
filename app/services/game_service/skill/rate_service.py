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
        # 1. Инициализируй счетчик для этого навыка
        total_xp_tick = 0.0

        # 2. Получи твой новый словарь весов из рецепта
        #    (используй .get() с {} на случай, если у навыка нет весов)
        stat_weights = recipe.get("stat_weights", {})

        # 3. Запусти *внутренний* цикл по твоему словарю весов
        for stat_name, multiplier in stat_weights.items():
            # 4. Безопасно получи значение стата из DTO
            #    (getattr нужен, т.к. stat_name - это строка)
            stat_value = getattr(stats_dto, stat_name, 0)

            # 5. Рассчитай вклад этого стата и добавь к счетчику
            total_xp_tick += stat_value * multiplier

        # 6. После внутреннего цикла, округли результат до int
        xp_tick_rate = int(total_xp_tick)


        rates_to_upsert.append({
            "character_id": character_id,
            "skill_key": skill_key,
            "xp_per_tick": xp_tick_rate
        })

    log.info(f"Для character_id={character_id} рассчитано {len(rates_to_upsert)} ставок БСО.")
    return rates_to_upsert
