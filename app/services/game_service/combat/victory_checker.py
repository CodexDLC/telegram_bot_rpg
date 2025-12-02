from loguru import logger as log

from app.resources.schemas_dto.combat_source_dto import CombatSessionContainerDTO


class VictoryChecker:
    """
    Сервис для проверки условий победы и поражения в боевой сессии.

    Анализирует состояние участников боя на предмет смерти и определяет,
    завершился ли бой и какая команда победила.
    """

    @staticmethod
    def check_death(actor: CombatSessionContainerDTO) -> bool:
        """
        Проверяет, мертв ли актор.

        Args:
            actor: DTO актора для проверки.

        Returns:
            True, если HP актора меньше или равно 0, иначе False.
        """
        is_dead = bool(actor.state and actor.state.hp_current <= 0)
        log.debug(f"VictoryChecker | action=check_death char_id={actor.char_id} is_dead={is_dead}")
        return is_dead

    @staticmethod
    def check_battle_end(participants_map: dict[int, CombatSessionContainerDTO]) -> str | None:
        """
        Проверяет, завершился ли бой, и определяет победителя.

        Бой считается завершенным, если осталась только одна живая команда
        или все участники мертвы (ничья).

        Args:
            participants_map: Словарь, где ключ — ID участника, а значение — его DTO.

        Returns:
            Строка с названием победившей команды ('blue', 'red'),
            'draw' в случае ничьей, или None, если бой продолжается.
        """
        teams_alive: set[str] = set()

        for actor in participants_map.values():
            if not actor or not actor.state:
                continue
            if actor.state.hp_current > 0:
                teams_alive.add(actor.team)

        if len(teams_alive) == 0:
            log.info(f"VictoryChecker | event=battle_ended result=draw participants={list(participants_map.keys())}")
            return "draw"
        elif len(teams_alive) == 1:
            winner_team = list(teams_alive)[0]
            log.info(
                f"VictoryChecker | event=battle_ended result=victory winner_team='{winner_team}' participants={list(participants_map.keys())}"
            )
            return winner_team

        log.debug("VictoryChecker | event=battle_continues")
        return None
