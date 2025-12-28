# TODO: DRAFT ARCHITECTURE (NOT IMPLEMENTED YET)
# Это черновик новой архитектуры Боя.
# Идея: Разделить оркестратор на InitService (Factory) и RuntimeService (Engine).
# Пока не используется.

# from typing import Any, TYPE_CHECKING
#
# from loguru import logger as log
#
# from apps.game_core.game_service.combat.combat_initialization_service import CombatInitializationService
# from apps.game_core.game_service.combat.combat_runtime_service import CombatRuntimeService
#
# if TYPE_CHECKING:
#     from apps.game_core.game_service.core_router import CoreRouter
#
#
# class CombatCoreOrchestrator:
#     """
#     Оркестратор Боя (Core Layer).
#     Единая точка входа для всех боевых взаимодействий.
#     Маршрутизирует запросы на создание (Init) и управление (Runtime).
#     """
#
#     def __init__(
#         self,
#         init_service: CombatInitializationService,
#         runtime_service: CombatRuntimeService,
#         core_router: "CoreRouter | None" = None,
#     ):
#         self.init_service = init_service
#         self.runtime_service = runtime_service
#         self.core_router = core_router
#
#     # --- Protocol Implementation ---
#
#     async def get_entry_point(self, char_id: int, action: str, context: dict[str, Any]) -> Any:
#         """
#         Единая точка входа. Диспетчер действий.
#         """
#         if action == "initialize":
#             # Диспетчеризация по типу боя
#             battle_type = context.get("battle_type", "pve")
#
#             if battle_type == "pve_tutorial":
#                 return await self._init_pve_tutorial(char_id, context)
#             elif battle_type == "pvp_arena":
#                 return await self._init_pvp_arena(char_id, context)
#             elif battle_type == "pve_exploration":
#                 return await self._init_pve_exploration(char_id, context)
#
#             raise ValueError(f"Unknown battle type: {battle_type}")
#
#         elif action == "view" or action == "resume":
#             return await self._resume_battle(char_id, context)
#
#         raise ValueError(f"Unknown action for Combat: {action}")
#
#     # --- Initialization Handlers ---
#
#     async def _init_pve_tutorial(self, char_id: int, context: dict[str, Any]) -> Any:
#         """Инициализация туториала (1 на 1 с известным монстром)."""
#         monster_data = context.get("monster_data")
#         location_id = context.get("location_id", "52_52")
#
#         if not monster_data:
#             raise ValueError("Monster data required for tutorial battle")
#
#         # 1. Создаем сессию через Фабрику
#         session_id = await self.init_service.create_pve_tutorial_battle(char_id, monster_data, location_id)
#
#         # 2. Возвращаем первый кадр через Движок
#         return await self.runtime_service.get_dashboard(session_id, char_id)
#
#     async def _init_pvp_arena(self, char_id: int, context: dict[str, Any]) -> Any:
#         """Инициализация PVP (заглушка)."""
#         raise NotImplementedError("PVP Arena not implemented yet")
#
#     async def _init_pve_exploration(self, char_id: int, context: dict[str, Any]) -> Any:
#         """Инициализация случайного боя (заглушка)."""
#         raise NotImplementedError("Exploration PVE not implemented yet")
#
#     # --- Runtime Handlers ---
#
#     async def _resume_battle(self, char_id: int, context: dict[str, Any]) -> Any:
#         """
#         Возвращает состояние текущего боя.
#         """
#         # 1. Пытаемся найти сессию в контексте
#         session_id = context.get("combat_session_id")
#
#         # 2. Если нет, ищем активную сессию игрока в Redis
#         if not session_id:
#             # TODO: Реализовать метод в CombatManager: get_active_session(char_id)
#             # session_id = await self.combat_manager.get_active_session(char_id)
#             pass
#
#         if not session_id:
#             raise ValueError("Session ID required for resume (and no active session found)")
#
#         return await self.runtime_service.get_dashboard(session_id, char_id)
