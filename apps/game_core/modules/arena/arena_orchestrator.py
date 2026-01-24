# import time
#
# from loguru import logger as log
# from sqlalchemy.ext.asyncio import AsyncSession
#
# from apps.common.core.settings import settings
# from apps.common.schemas_dto.game.arena_dto import ArenaMatchResponse, ArenaQueueResponse
# from apps.common.services.redis.manager.account_manager import AccountManager
# from apps.common.services.redis.manager.arena_manager import ArenaManager
# from apps.common.services.redis.manager.combat_manager import CombatManager
# from apps.game_core.modules.arena.service_1v1 import Arena1v1Service
#
#
# class ArenaCoreOrchestrator:
#     """
#     Оркестратор для бизнес-логики Арены.
#     Инкапсулирует логику принятия решений (например, когда создавать тень).
#     """
#
#     def __init__(
#         self,
#         session: AsyncSession,
#         account_manager: AccountManager,
#         arena_manager: ArenaManager,
#         combat_manager: CombatManager,
#     ):
#         self.session = session
#         self.account_manager = account_manager
#         self.arena_manager = arena_manager
#         self.combat_manager = combat_manager
#
#     async def process_toggle_queue(self, mode: str, char_id: int) -> ArenaQueueResponse:
#         """
#         Обрабатывает постановку или снятие с очереди.
#         Если игрок в очереди - снимает. Если нет - ставит.
#         """
#         service = self._get_service_by_mode(mode, char_id)
#         if not service:
#             return ArenaQueueResponse(status="error", message="Invalid mode")
#
#         # Проверяем, есть ли уже заявка в редисе
#         request_meta = await self.arena_manager.get_request(char_id)
#
#         if request_meta:
#             # Если заявка есть - отменяем очередь
#             await service.cancel_queue()
#             log.info(f"Orchestrator | Canceled queue for char_id={char_id}")
#             return ArenaQueueResponse(status="cancelled")
#         else:
#             # Если заявки нет - ставим в очередь
#             gs = await service.join_queue()
#             log.info(f"Orchestrator | Joined queue for char_id={char_id} with gs={gs}")
#             return ArenaQueueResponse(status="joined", gs=gs)
#
#     async def process_check_match(self, mode: str, char_id: int) -> ArenaMatchResponse:
#         """
#         Проверяет наличие матча. Если ожидание слишком долгое - создает бой с тенью.
#         """
#         service = self._get_service_by_mode(mode, char_id)
#         if not service:
#             return ArenaMatchResponse(status="error")
#
#         # 1. Проверяем, нашелся ли уже для нас бой
#         session_id = await service.check_and_match(attempt=1)  # attempt=1 для узкого поиска
#         if session_id:
#             log.info(f"Orchestrator | Match found for char_id={char_id}, session_id={session_id}")
#             # TODO: Добавить получение метаданных о противнике
#             return ArenaMatchResponse(status="found", session_id=session_id)
#
#         # 2. Если бой не найден, проверяем время ожидания
#         request_meta = await self.arena_manager.get_request(char_id)
#         if not request_meta:
#             # Это может случиться, если очередь была отменена в другом месте
#             log.warning(f"Orchestrator | No request found for char_id={char_id} during check.")
#             return ArenaMatchResponse(status="error")
#
#         start_time = request_meta.get("start_time", time.time())
#         wait_duration = time.time() - start_time
#
#         # 3. Сравниваем с таймаутом из настроек
#         if wait_duration > settings.arena_matchmaking_timeout:
#             log.info(f"Orchestrator | Timeout for char_id={char_id}. Creating shadow battle.")
#             session_id = await service.create_shadow_battle()
#             return ArenaMatchResponse(status="created_shadow", session_id=session_id, is_shadow=True)
#         else:
#             # Если время не вышло - просто ждем
#             log.debug(f"Orchestrator | Waiting for match for char_id={char_id}. Wait time: {wait_duration:.2f}s")
#             return ArenaMatchResponse(status="waiting")
#
#     def _get_service_by_mode(self, mode: str, char_id: int) -> Arena1v1Service | None:
#         """Фабричный метод для получения нужного сервиса по режиму игры."""
#         if mode == "1v1":
#             return Arena1v1Service(self.session, char_id, self.arena_manager, self.combat_manager, self.account_manager)
#         # Добавить другие режимы по мере их появления
#         return None
