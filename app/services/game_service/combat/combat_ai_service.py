import json
import random
from typing import Any

from loguru import logger as log

from app.resources.schemas_dto.combat_source_dto import CombatSessionContainerDTO
from app.services.core_service.manager.combat_manager import combat_manager
from app.services.game_service.combat.ability_service import AbilityService


class CombatAIService:
    """
    Сервис принятия решений для NPC (Искусственный Интеллект) в боевых сессиях.

    Отвечает за выбор цели, способности, зон атаки и защиты для AI-акторов.
    """

    @staticmethod
    async def calculate_action(
        actor_dto: CombatSessionContainerDTO,
        session_id: str,
    ) -> dict[str, Any]:
        """
        Принимает решение за NPC: кого атаковать, какую способность использовать,
        какие зоны атаковать и как защищаться.

        Args:
            actor_dto: DTO актора, для которого принимается решение.
            session_id: Идентификатор текущей боевой сессии.

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

        all_ids = await combat_manager.get_session_participants(session_id)
        enemies: list[int] = []
        threats: list[int] = []

        for pid in all_ids:
            pid_int = int(pid)
            if pid_int == char_id:
                continue

            raw_target = await combat_manager.get_actor_json(session_id, pid_int)
            if not raw_target:
                continue

            try:
                target_obj = json.loads(raw_target)
            except json.JSONDecodeError:
                log.error(
                    f"CombatAIService | status=failed reason='JSON decode error for target' target_id={pid_int} session_id='{session_id}'",
                    exc_info=True,
                )
                continue

            hp = target_obj.get("state", {}).get("hp_current", 0)
            if target_obj.get("team") != my_team and hp > 0:
                enemies.append(pid_int)
                pending = await combat_manager.get_pending_move(session_id, pid_int, char_id)
                if pending:
                    threats.append(pid_int)

        target_id: int | None = None
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
