# app/services/game_service/matchmaking_service.py
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.core_service.manager.account_manager import account_manager
from app.services.game_service.stats_aggregation_service import StatsAggregationService
from database.repositories import get_leaderboard_repo

# Веса характеристик (Баланс)
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
    # Боевые модификаторы (самые дорогие)
    "physical_damage_bonus": 200.0,
    "magical_damage_bonus": 200.0,
    "physical_crit_chance": 200.0,
    "magical_crit_chance": 200.0,
    "dodge_chance": 200.0,
}


class MatchmakingService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.aggregator = StatsAggregationService(session)

        self.lb_repo = get_leaderboard_repo(session)

    async def calculate_raw_gs(self, char_id: int) -> int:
        """Чистый расчет GS на основе статов."""
        total_data = await self.aggregator.get_character_total_stats(char_id)
        if not total_data:
            return 10

        score = 0.0

        # Собираем все статы (базовые и моды) в одну кучу
        all_stats = {}
        for category in ["stats", "modifiers"]:
            for key, info in total_data.get(category, {}).items():
                all_stats[key] = float(info.get("total", 0))

        for key, val in all_stats.items():
            weight = GS_WEIGHTS.get(key, 0.0)
            if weight == 0.0:
                # Фоллбэки для неизвестных статов
                if "damage" in key:
                    weight = 1.0
                elif "chance" in key:
                    weight = 100.0
                elif "resistance" in key:
                    weight = 50.0

            score += val * weight

        return max(10, int(score))

    async def refresh_gear_score(self, char_id: int) -> int:
        """
        Главный метод обновления силы.
        Пишет в Redis (Кэш) и Leaderboard SQL (Поиск/Топ).
        """
        # 1. Считаем
        gs = await self.calculate_raw_gs(char_id)

        # 2. Redis (Быстрый доступ)
        await account_manager.update_account_fields(char_id, {"gear_score": gs})

        # 3. SQL Leaderboard (Долгосрочное хранение и поиск)
        await self.lb_repo.update_score(char_id, gear_score=gs)

        log.info(f"GearScore synced for {char_id}: {gs}")
        return gs

    async def get_cached_gs(self, char_id: int) -> int:
        """Берет из кэша или считает, если пусто."""
        val = await account_manager.get_account_field(char_id, "gear_score")
        if val:
            return int(val)
        return await self.refresh_gear_score(char_id)
