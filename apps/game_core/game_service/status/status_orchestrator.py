from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.database.repositories import (
    get_character_repo,
    get_character_stats_repo,
    get_skill_progress_repo,
    get_symbiote_repo,
)
from apps.common.schemas_dto.status_dto import FullCharacterDataDTO, SkillProgressDTO, SymbioteReadDTO
from apps.game_core.game_service.status.stats_aggregation_service import StatsAggregationService


class StatusCoreOrchestrator:
    """
    Оркестратор статуса персонажа (Core Layer).
    Собирает данные о персонаже из разных источников.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.char_repo = get_character_repo(session)
        self.stats_repo = get_character_stats_repo(session)
        self.symbiote_repo = get_symbiote_repo(session)
        self.skill_repo = get_skill_progress_repo(session)
        self.agg_service = StatsAggregationService(session)

    async def get_full_character_data(self, char_id: int) -> FullCharacterDataDTO | None:
        """
        Возвращает полные данные о персонаже.
        """
        # 1. Основные данные
        character = await self.char_repo.get_character(char_id)
        if not character:
            return None

        # 2. Базовые статы
        stats = await self.stats_repo.get_stats(char_id)
        if not stats:
            # Если статов нет, это ошибка данных, но вернем None
            return None

        # 3. Симбиот
        symbiote_orm = await self.symbiote_repo.get_symbiote(char_id)
        symbiote_dto = None
        if symbiote_orm:
            # Исправлено: убрано обращение к несуществующему полю level
            # Используем gift_rank как аналог уровня, если это подразумевалось
            symbiote_dto = SymbioteReadDTO(
                symbiote_name=symbiote_orm.symbiote_name,
                level=symbiote_orm.gift_rank,  # Используем gift_rank вместо level
                experience=symbiote_orm.gift_xp,  # Используем gift_xp вместо experience
            )

        # 4. Навыки
        skills_orm = await self.skill_repo.get_all_skills_progress(char_id)
        skills_dto = [
            SkillProgressDTO(
                character_id=s.character_id,
                skill_key=s.skill_key,
                total_xp=s.total_xp,
                is_unlocked=s.is_unlocked,
                progress_state=s.progress_state,
                created_at=s.created_at,
                updated_at=s.updated_at,
            )
            for s in skills_orm
        ]

        # 5. Агрегированные статы (с учетом бонусов)
        total_stats = await self.agg_service.get_character_total_stats(char_id)

        return FullCharacterDataDTO(
            character=character, stats=stats, symbiote=symbiote_dto, skills=skills_dto, total_stats=total_stats or {}
        )
