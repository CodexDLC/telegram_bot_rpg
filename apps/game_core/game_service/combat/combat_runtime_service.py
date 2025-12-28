# TODO: DRAFT ARCHITECTURE (NOT IMPLEMENTED YET)
# from typing import Any
#
# from loguru import logger as log
#
# from apps.common.schemas_dto.combat_source_dto import (
#     ActorSnapshotDTO,
#     CombatDashboardDTO,
#     CombatSessionContainerDTO,
#     StatSourceData,
# )
# from apps.common.services.core_service.manager.account_manager import AccountManager
# from apps.common.services.core_service.manager.combat_manager import CombatManager
# from apps.game_core.game_service.combat.core.combat_stats_calculator import StatsCalculator
#
#
# class CombatRuntimeService:
#     """
#     Движок боевой сессии.
#     Управляет состоянием уже созданного боя.
#     """
#
#     def __init__(self, combat_manager: CombatManager, account_manager: AccountManager):
#         self.combat_manager = combat_manager
#         self.account_manager = account_manager
#
#     async def get_dashboard(self, session_id: str, char_id: int) -> CombatDashboardDTO:
#         """
#         Собирает данные для UI.
#         """
#         # 1. Метаданные
#         meta = await self.combat_manager.get_rbc_session_meta(session_id)
#         if not meta:
#             raise ValueError(f"Session meta not found for session {session_id}")
#
#         is_active = int(meta.get("active", 1)) == 1
#         status = "active" if is_active else "finished"
#         winner = meta.get("winner")
#
#         # 2. Состояние бойцов
#         all_actors_raw = await self.combat_manager.get_rbc_all_actors_json(session_id)
#         if not all_actors_raw:
#             raise ValueError(f"No actors found for session {session_id}")
#
#         snapshots: dict[int, ActorSnapshotDTO] = {}
#         player_team = "blue"
#
#         for aid_str, raw_json in all_actors_raw.items():
#             aid = int(aid_str)
#             container = CombatSessionContainerDTO.model_validate_json(raw_json)
#
#             # Считаем Максимумы (на лету, так как они могут зависеть от баффов)
#             hp_max = int(StatsCalculator.calculate("hp_max", container.stats.get("hp_max", StatSourceData(base=100))))
#             en_max = int(StatsCalculator.calculate("energy_max", container.stats.get("energy_max", StatSourceData(base=100))))
#
#             snapshots[aid] = ActorSnapshotDTO(
#                 char_id=aid,
#                 name=container.name,
#                 hp_current=container.state.hp_current if container.state else 0,
#                 hp_max=hp_max,
#                 energy_current=container.state.energy_current if container.state else 0,
#                 energy_max=en_max,
#                 team=container.team,
#                 is_dead=bool(container.state and container.state.hp_current <= 0),
#                 effects=list(container.state.effects.keys()) if container.state else [],
#                 tokens=container.state.tokens if container.state else {},
#             )
#             if aid == char_id:
#                 player_team = container.team
#
#         # 3. Очередь и Цель
#         queue_len = await self.combat_manager.get_rbc_queue_length(session_id, char_id)
#         target_id = await self.combat_manager.get_rbc_next_target_id(session_id, char_id)
#
#         # 4. Статус ожидания
#         if is_active:
#             moves = await self.combat_manager.get_rbc_moves(session_id, char_id)
#             if moves:
#                 status = "waiting"
#
#         player_snap = snapshots.get(char_id)
#         if not player_snap:
#              # Если игрока нет (например, наблюдатель), берем первого попавшегося или кидаем ошибку
#              # Пока кидаем ошибку
#              raise ValueError(f"Player {char_id} not found in session {session_id}")
#
#         return CombatDashboardDTO(
#             session_id=session_id,
#             status=status,
#             player=player_snap,
#             current_target=snapshots.get(target_id) if target_id else None,
#             enemies=[s for s in snapshots.values() if s.team != player_team],
#             allies=[s for s in snapshots.values() if s.team == player_team and s.char_id != char_id],
#             queue_count=queue_len,
#             switch_charges=player_snap.tokens.get("tactics", 0),
#             last_logs=[], # TODO: Логи
#             winner_team=winner,
#         )
