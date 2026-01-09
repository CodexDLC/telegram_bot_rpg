# # apps/game_core/modules/combats/core/combat_victory_checker.py
# from loguru import logger as log
#
# from apps.common.schemas_dto import CombatSessionContainerDTO
#
#
# class VictoryChecker:
#     """
#     Сервис для проверки условий победы и поражения в боевой сессии.
#
#     Анализирует состояние участников боя на предмет смерти и определяет,
#     завершился ли бой и какая команда победила.
#     """
#
#     @staticmethod
#     def check_death(actor: CombatSessionContainerDTO) -> bool:
#         """
#         Проверяет, мертв ли актор.
#
#         Args:
#             actor: DTO актора для проверки.
#
#         Returns:
#             True, если HP актора меньше или равно 0, иначе False.
#         """
#         is_dead = bool(actor.state and actor.state.hp_current <= 0)
#         # log.debug(f"VictoryChecker | action=check_death char_id={actor.char_id} is_dead={is_dead}")
#         return is_dead
#
#     @staticmethod
#     def check_battle_end(teams: dict[str, list[int]], dead_actors: set[int]) -> str | None:
#         """
#         Проверяет, завершился ли бой, и определяет победителя.
#         Использует данные из метаданных сессии (teams, dead_actors).
#
#         Args:
#             teams: Словарь команд {team_name: [member_ids]}.
#             dead_actors: Множество ID мертвых участников.
#
#         Returns:
#             Строка с названием победившей команды ('blue', 'red'),
#             'draw' в случае ничьей, или None, если бой продолжается.
#         """
#         alive_teams = set()
#
#         for team_name, members in teams.items():
#             # Команда жива, если хотя бы один участник НЕ в списке мертвых
#             if any(m for m in members if m not in dead_actors):
#                 alive_teams.add(team_name)
#
#         if len(alive_teams) == 0:
#             log.info("VictoryChecker | event=battle_ended result=draw")
#             return "draw"
#         elif len(alive_teams) == 1:
#             winner_team = list(alive_teams)[0]
#             log.info(f"VictoryChecker | event=battle_ended result=victory winner_team='{winner_team}'")
#             return winner_team
#
#         log.debug("VictoryChecker | event=battle_continues")
#         return None
