# app/services/game_service/combat/victory_checker.py

from loguru import logger as log

from app.resources.schemas_dto.combat_source_dto import CombatSessionContainerDTO


class VictoryChecker:
    """Анализирует состояние бойцов на предмет смерти и окончания боя."""

    @staticmethod
    def check_death(actor: CombatSessionContainerDTO) -> bool:
        """
        Возвращает True, если боец умер.

        Args:
            actor: DTO актора.

        Returns:
            True, если HP <= 0.
        """
        return bool(actor.state and actor.state.hp_current <= 0)

    @staticmethod
    def check_battle_end(participants_map: dict[int, CombatSessionContainerDTO]) -> str | None:
        """
        Проверяет, остались ли живые команды.

        Args:
            participants_map: Словарь с участниками боя.

        Returns:
            Имя победившей команды ('blue', 'red'), 'draw' или None, если бой продолжается.
        """
        teams_alive: set[str] = set()

        for actor in participants_map.values():
            if not actor or not actor.state:
                continue
            if actor.state.hp_current > 0:
                teams_alive.add(actor.team)

        if len(teams_alive) == 0:
            log.info(f"BattleEndCheck | result=draw participants={list(participants_map.keys())}")
            return "draw"  # Все умерли
        elif len(teams_alive) == 1:
            winner_team = list(teams_alive)[0]
            log.info(
                f"BattleEndCheck | result=victory winner_team={winner_team} participants={list(participants_map.keys())}"
            )
            return winner_team

        return None
