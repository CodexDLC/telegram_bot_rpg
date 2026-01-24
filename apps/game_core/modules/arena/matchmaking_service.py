# from loguru import logger as log
# from sqlalchemy.ext.asyncio import AsyncSession
#
# from apps.common.database.repositories import get_leaderboard_repo
# from apps.common.services.redis.manager.account_manager import AccountManager
# from apps.game_core.modules.status.stats_aggregation_service import StatsAggregationService
# from apps.game_core.resources.balance import GS_DIVISORS
#
#
# class MatchmakingService:
#     """
#     Сервис для расчета и управления Gear Score (GS) персонажей.
#     """
#
#     def __init__(self, session: AsyncSession, account_manager: AccountManager):
#         self.session = session
#         self.aggregator = StatsAggregationService(session)
#         self.lb_repo = get_leaderboard_repo(session)
#         self.account_manager = account_manager
#         log.debug("MatchmakingService | status=initialized")
#
#     async def calculate_raw_gs(self, char_id: int) -> int:
#         """
#         Рассчитывает "сырой" Gear Score (GS) персонажа на основе его модификаторов.
#         """
#         total_data = await self.aggregator.get_character_total_stats(char_id)
#         if not total_data:
#             log.warning(f"Matchmaking | status=failed reason='No total stats found' char_id={char_id}")
#             return 10
#
#         score = 0.0
#         modifiers = total_data.get("modifiers", {})
#
#         for key, info in modifiers.items():
#             stat_value = float(info.get("total", 0))
#             if stat_value == 0:
#                 continue
#
#             divisor = GS_DIVISORS.get(key)
#             if not divisor or divisor == 0.0:
#                 continue
#
#             # Новая, упрощенная формула: Значение / Делитель
#             stat_gs = stat_value / divisor
#             score += stat_gs
#
#         log.debug(f"Matchmaking | action=calculate_raw_gs char_id={char_id} raw_gs={int(score)}")
#         return max(10, int(score))
#
#     async def refresh_gear_score(self, char_id: int) -> int:
#         """
#         Обновляет Gear Score персонажа, сохраняя его в Redis и SQL Leaderboard.
#         """
#         gs = await self.calculate_raw_gs(char_id)
#         await self.account_manager.update_account_fields(char_id, {"gear_score": gs})
#         await self.lb_repo.update_score(char_id, gear_score=gs)
#         log.info(f"Matchmaking | event=gs_synced char_id={char_id} gs={gs}")
#         return gs
#
#     async def get_cached_gs(self, char_id: int) -> int:
#         """
#         Получает Gear Score персонажа из кэша Redis.
#         """
#         val = await self.account_manager.get_account_field(char_id, "gear_score")
#         if val:
#             log.debug(f"Matchmaking | action=get_cached_gs status=hit char_id={char_id} gs={val}")
#             return int(val)
#         log.info(f"Matchmaking | action=get_cached_gs status=miss char_id={char_id} action=refresh_gs")
#         return await self.refresh_gear_score(char_id)
