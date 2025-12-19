import json
import random
from typing import Any

from loguru import logger as log
from pydantic import ValidationError

from apps.common.schemas_dto import CombatSessionContainerDTO
from apps.common.services.core_service import CombatManager
from apps.game_core.game_service.combat.mechanics.combat_ability_service import AbilityService


class CombatAIService:
    """
    Сервис принятия решений для NPC (Искусственный Интеллект) в боевых сессиях.

    Отвечает за выбор цели, способности, зон атаки и защиты для AI-акторов.
    """

    def __init__(self, combat_manager: CombatManager):
        self.combat_manager = combat_manager

    async def calculate_action(
        self,
        actor_dto: CombatSessionContainerDTO,
        session_id: str,
        target_id: int | None = None,
    ) -> dict[str, Any]:
        """
        Принимает решение за NPC: кого атаковать, какую способность использовать,
        какие зоны атаковать и как защищаться.

        Args:
            actor_dto: DTO актора, для которого принимается решение.
            session_id: Идентификатор текущей боевой сессии.
            target_id: Если цель уже известна (например, ответный удар), можно передать её ID.

        Returns:
            Словарь, содержащий решение AI:
            - `target_id`: Идентификатор выбранной цели.
            - `attack`: Список зон атаки.
            - `block`: Список зон блокировки.
            - `ability`: Ключ выбранной способности (может быть None).
            Возвращает пустой словарь, если цель не найдена.
        """
        char_id = actor_dto.char_id
        my_team = actor_dto.team
        log.debug(f"CombatAIService | action=calculate_action actor_id={char_id} session_id='{session_id}'")

        # Если цель не передана, ищем её
        if target_id is None:
            all_actors_json = await self.combat_manager.get_rbc_all_actors_json(session_id)
            if not all_actors_json:
                return {}

            enemies: list[int] = []
            threats: list[int] = []

            for pid_str, raw_json in all_actors_json.items():
                pid_int = int(pid_str)
                if pid_int == char_id:
                    continue

                try:
                    target_obj = CombatSessionContainerDTO.model_validate_json(raw_json)
                except (ValidationError, json.JSONDecodeError):
                    continue

                hp = target_obj.state.hp_current if target_obj.state else 0
                if target_obj.team != my_team and hp > 0:
                    enemies.append(pid_int)
                    # Проверяем, сделал ли этот враг ход против нас
                    moves = await self.combat_manager.get_rbc_moves(session_id, pid_int)
                    if moves and str(char_id) in moves:
                        threats.append(pid_int)

            if threats:
                target_id = random.choice(threats)
                log.debug(f"CombatAIService | target_strategy=threat actor_id={char_id} target_id={target_id}")
            elif enemies:
                target_id = random.choice(enemies)
                log.debug(f"CombatAIService | target_strategy=random_enemy actor_id={char_id} target_id={target_id}")
            else:
                log.warning(
                    f"CombatAIService | status=failed reason='No target found' actor_id={char_id} session_id='{session_id}'"
                )
                return {}

        selected_ability: str | None = None
        if actor_dto.active_abilities:
            shuffled_skills = actor_dto.active_abilities.copy()
            random.shuffle(shuffled_skills)

            for skill_key in shuffled_skills:
                is_ok, _ = AbilityService.can_use_ability(actor_dto, skill_key)
                if is_ok:
                    selected_ability = skill_key
                    log.info(f"CombatAIService | ability_selected actor_id={char_id} ability_key='{skill_key}'")
                    break

        all_zones = ["head", "chest", "belly", "legs", "feet"]
        attack_zones = [random.choice(all_zones)]

        valid_pairs = [
            ["head", "chest"],
            ["chest", "belly"],
            ["belly", "legs"],
            ["legs", "feet"],
            ["feet", "head"],
        ]
        block_zones = random.choice(valid_pairs)

        decision = {
            "target_id": target_id,
            "attack": attack_zones,
            "block": block_zones,
            "ability": selected_ability,
        }
        log.info(
            f"CombatAIService | decision_made actor_id={char_id} target_id={target_id} ability='{selected_ability}'"
        )
        return decision
