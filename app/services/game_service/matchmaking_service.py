from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.core_service.manager.account_manager import account_manager
from app.services.game_service.stats_aggregation_service import StatsAggregationService
from database.repositories import get_leaderboard_repo

GS_WEIGHTS = {
    "strength": 2.0,
    "agility": 2.0,
    "intelligence": 2.0,
    "wisdom": 2.0,
    "endurance": 2.0,
    "men": 2.0,
    "perception": 1.0,
    "luck": 1.0,
    "charisma": 1.0,
    "hp_max": 0.2,
    "energy_max": 0.2,
    "physical_damage_bonus": 200.0,
    "magical_damage_bonus": 200.0,
    "physical_crit_chance": 200.0,
    "magical_crit_chance": 200.0,
    "dodge_chance": 200.0,
}


class MatchmakingService:
    """
    Сервис для расчета и управления Gear Score (GS) персонажей.

    Отвечает за вычисление GS на основе агрегированных характеристик,
    сохранение его в Redis для быстрого доступа и в SQL Leaderboard
    для долгосрочного хранения и поиска.
    """

    def __init__(self, session: AsyncSession):
        """
        Инициализирует MatchmakingService.

        Args:
            session: Асинхронная сессия базы данных.
        """
        self.session = session
        self.aggregator = StatsAggregationService(session)
        self.lb_repo = get_leaderboard_repo(session)
        log.debug("MatchmakingService | status=initialized")

    async def calculate_raw_gs(self, char_id: int) -> int:
        """
        Рассчитывает "сырой" Gear Score (GS) персонажа на основе его характеристик.

        Использует веса, определенные в `GS_WEIGHTS`, для оценки вклада каждой
        характеристики в общий GS.

        Args:
            char_id: Уникальный идентификатор персонажа.

        Returns:
            Целочисленное значение Gear Score, не менее 10.
        """
        total_data = await self.aggregator.get_character_total_stats(char_id)
        if not total_data:
            log.warning(f"Matchmaking | status=failed reason='No total stats found' char_id={char_id}")
            return 10

        score = 0.0
        all_stats: dict[str, float] = {}
        for category in ["stats", "modifiers"]:
            for key, info in total_data.get(category, {}).items():
                all_stats[key] = float(info.get("total", 0))

        for key, val in all_stats.items():
            weight = GS_WEIGHTS.get(key, 0.0)
            if weight == 0.0:
                if "damage" in key:
                    weight = 1.0
                elif "chance" in key:
                    weight = 100.0
                elif "resistance" in key:
                    weight = 50.0
            score += val * weight

        log.debug(f"Matchmaking | action=calculate_raw_gs char_id={char_id} raw_gs={int(score)}")
        return max(10, int(score))

    async def refresh_gear_score(self, char_id: int) -> int:
        """
        Обновляет Gear Score персонажа, сохраняя его в Redis и SQL Leaderboard.

        Args:
            char_id: Уникальный идентификатор персонажа.

        Returns:
            Актуальное значение Gear Score персонажа.
        """
        gs = await self.calculate_raw_gs(char_id)
        await account_manager.update_account_fields(char_id, {"gear_score": gs})
        await self.lb_repo.update_score(char_id, gear_score=gs)
        log.info(f"Matchmaking | event=gs_synced char_id={char_id} gs={gs}")
        return gs

    async def get_cached_gs(self, char_id: int) -> int:
        """
        Получает Gear Score персонажа из кэша Redis.

        Если GS отсутствует в кэше, он будет рассчитан и обновлен.

        Args:
            char_id: Уникальный идентификатор персонажа.

        Returns:
            Актуальное значение Gear Score персонажа.
        """
        val = await account_manager.get_account_field(char_id, "gear_score")
        if val:
            log.debug(f"Matchmaking | action=get_cached_gs status=hit char_id={char_id} gs={val}")
            return int(val)
        log.info(f"Matchmaking | action=get_cached_gs status=miss char_id={char_id} action=refresh_gs")
        return await self.refresh_gear_score(char_id)
