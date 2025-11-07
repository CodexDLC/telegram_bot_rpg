# app/services/game_service/skill/skill_service.py
import logging
from typing import Optional, Dict

from database.db_contract.i_characters_repo import ICharacterStatsRepo
from database.db_contract.i_skill_repo import ISkillRateRepo, ISkillProgressRepo
from app.resources.schemas_dto.character_dto import CharacterStatsReadDTO
from app.services.game_service.skill.rate_service import calculate_rates_data

log = logging.getLogger(__name__)


class CharacterSkillsService:
    """
    Фасад (Координатор) для управления бизнес-логикой навыков.

    Этот сервис оркестрирует взаимодействие между различными репозиториями
    (статы, ставки, прогресс) для выполнения сложных операций, таких как
    финализация туториала. Он инкапсулирует логику, скрывая детали
    реализации от хэндлеров.
    """

    def __init__(
            self,
            stats_repo: ICharacterStatsRepo,
            rate_repo: ISkillRateRepo,
            progress_repo: ISkillProgressRepo,
    ):
        """
        Инициализирует сервис с помощью инъекции зависимостей.

        Args:
            stats_repo (ICharacterStatsRepo): Репозиторий для работы с характеристиками.
            rate_repo (ISkillRateRepo): Репозиторий для работы со ставками опыта (БСО).
            progress_repo (ISkillProgressRepo): Репозиторий для работы с прогрессом навыков.
        """
        self._stats_repo = stats_repo
        self._rate_repo = rate_repo
        self._progress_repo = progress_repo
        log.debug(f"{self.__class__.__name__} инициализирован с репозиториями.")

    async def finalize_tutorial_stats(
            self,
            character_id: int,
            bonus_stats: Dict[str, int]
    ) -> Optional[CharacterStatsReadDTO]:
        """
        Финализирует распределение очков после туториала S.P.E.C.I.A.L.

        Выполняет 3 критических шага в рамках одной транзакции (предполагается,
        что сессия управляется извне, например, через Unit of Work):
        1. Атомарно добавляет бонусные очки к характеристикам персонажа.
        2. Инициализирует все базовые навыки персонажа с 0 XP.
        3. Рассчитывает и сохраняет "Базовую Ставку Опыта" (БСО) для всех навыков.

        Args:
            character_id (int): ID персонажа.
            bonus_stats (Dict[str, int]): Словарь с бонусами к характеристикам.

        Returns:
            Optional[CharacterStatsReadDTO]: DTO с финальными (обновленными)
                                             характеристиками, если все прошло
                                             успешно. Иначе - None.
        """
        log.info(f"Начало финализации статов туториала для character_id={character_id} с бонусами: {bonus_stats}")

        # Шаг 1: Применение финальных статов S.P.E.C.I.A.L.
        log.debug(f"Шаг 1/3: Добавление бонусных статов для character_id={character_id}.")
        final_stats_dto = await self._stats_repo.add_stats(character_id, bonus_stats)
        if not final_stats_dto:
            log.error(f"Не удалось применить бонусные статы для character_id={character_id}. Операция прервана.")
            return None
        log.debug(f"Финальные статы для character_id={character_id} успешно применены.")

        # Шаг 2: Инициализация всех базовых навыков с 0 XP.
        log.debug(f"Шаг 2/3: Инициализация базовых навыков для character_id={character_id}.")
        await self._progress_repo.initialize_all_base_skills(character_id)
        log.debug(f"Базовые навыки для character_id={character_id} успешно инициализированы.")

        # Шаг 3: Расчет и сохранение БСО.
        log.debug(f"Шаг 3/3: Расчет и сохранение БСО для character_id={character_id}.")
        rates_data = calculate_rates_data(character_id, final_stats_dto)
        await self._rate_repo.upsert_skill_rates(rates_data)
        log.debug(f"БСО для character_id={character_id} успешно рассчитаны и сохранены.")

        log.info(f"Успешная финализация туториала S.P.E.C.I.A.L. для character_id={character_id}.")
        return final_stats_dto
