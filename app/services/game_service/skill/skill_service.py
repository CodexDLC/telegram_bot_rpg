import logging
from typing import Optional, Dict

from sqlalchemy.ext.asyncio import AsyncSession
# Импортируем Репозитории (Зависимости)
from database.db_contract.i_characters_repo import ICharacterStatsRepo
from database.db_contract.i_skill_repo import ISkillRateRepo, ISkillProgressRepo
# Импортируем DTO и Хелперы
from app.resources.schemas_dto.character_dto import CharacterStatsReadDTO
from app.services.game_service.skill.rate_service import calculate_rates_data  # <-- Хелпер

log = logging.getLogger(__name__)


class CharacterSkillsService:
    """
    Фасад (Координатор), который управляет всей бизнес-логикой
    S.P.E.C.I.A.L. -> Навыки -> БСО.

    Он отвечает за инициализацию навыков, пересчет ставок и
    координацию Репозиториев.
    """

    def __init__(
            self,
            stats_repo: ICharacterStatsRepo,
            rate_repo: ISkillRateRepo,
            progress_repo: ISkillProgressRepo,
    ):
        """
        Инъекция Зависимостей (Dependency Injection).
        Сервис-Фасад знает только о контрактах Репозиториев.
        """
        self._stats_repo = stats_repo
        self._rate_repo = rate_repo
        self._progress_repo = progress_repo

    async def finalize_tutorial_stats(
            self,
            character_id: int,
            bonus_stats: Dict[str, int]
    ) -> Optional[CharacterStatsReadDTO]:
        """
        Главный метод, который запускается после туториала S.P.E.C.I.A.L.
        Он выполняет 3 критических шага:
        1. Применяет финальные статы.
        2. Рассчитывает и сохраняет БСО для всех навыков.
        3. Инициализирует все базовые навыки с 0 XP.
        """

        # 1. Применяем финальные статы S.P.E.C.I.A.L. (через StatsRepo)
        # Мы используем метод, который ты ранее нашел, он возвращает DTO
        final_stats_dto = await self._stats_repo.add_stats(character_id, bonus_stats)

        if not final_stats_dto:
            log.error(f"Не удалось применить статы для char_id={character_id}")
            return None

        # 2. Инициализируем ВСЕ базовые навыки с 0 XP (через ProgressRepo)
        # Это гарантирует, что авто-прокачка будет работать сразу.
        await self._progress_repo.initialize_all_base_skills(character_id)

        # 3. Рассчитываем и сохраняем БСО (через Хелпер и RateRepo)
        # Хелпер готовит данные
        rates_data = calculate_rates_data(character_id, final_stats_dto)

        # Репозиторий атомарно сохраняет
        await self._rate_repo.upsert_skill_rates(rates_data)

        log.info(f"Успешная финализация туториала S.P.E.C.I.A.L. для char_id={character_id}.")
        return final_stats_dto