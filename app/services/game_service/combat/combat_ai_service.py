# app/services/game_service/combat/combat_ai_service.py
import json
import random
from typing import Any

from loguru import logger as log

from app.resources.schemas_dto.combat_source_dto import CombatSessionContainerDTO
from app.services.core_service.manager.combat_manager import combat_manager
from app.services.game_service.combat.ability_service import AbilityService


class CombatAIService:
    """
    Сервис принятия решений для NPC (Искусственный Интеллект).
    """

    @staticmethod
    async def calculate_action(
        actor_dto: CombatSessionContainerDTO,
        session_id: str,
    ) -> dict[str, Any]:
        """
        Принимает решение за NPC: кого бить, чем бить и как защищаться.

        Args:
            actor_dto: DTO актора, который делает ход.
            session_id: ID сессии боя.

        Returns:
            Словарь с решением (target_id, attack, block, ability) или пустой словарь.
        """
        char_id = actor_dto.char_id
        my_team = actor_dto.team
        log.debug(f"AICalculateAction | actor_id={char_id} session_id={session_id}")

        # 1. Получаем список всех участников
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
                    f"AIActionParseFail | reason=json_decode_error target_id={pid_int} session_id={session_id}",
                    exc_info=True,
                )
                continue

            # Фильтр: Враг и Живой
            hp = target_obj.get("state", {}).get("hp_current", 0)
            if target_obj.get("team") != my_team and hp > 0:
                enemies.append(pid_int)

                # Проверяем, не целится ли он в меня
                pending = await combat_manager.get_pending_move(session_id, pid_int, char_id)
                if pending:
                    threats.append(pid_int)

        # 2. Выбор Цели
        target_id: int | None = None
        if threats:
            target_id = random.choice(threats)
            log.debug(f"AITargetSelection | actor_id={char_id} strategy=threat target_id={target_id} threats={threats}")
        elif enemies:
            target_id = random.choice(enemies)
            log.debug(
                f"AITargetSelection | actor_id={char_id} strategy=random_enemy target_id={target_id} enemies={enemies}"
            )
        else:
            log.warning(f"AINoTargetFound | actor_id={char_id} session_id={session_id}")
            return {}

        # 3. Выбор Способности
        selected_ability: str | None = None
        if actor_dto.active_abilities:
            shuffled_skills = actor_dto.active_abilities.copy()
            random.shuffle(shuffled_skills)

            for skill_key in shuffled_skills:
                is_ok, _ = AbilityService.can_use_ability(actor_dto, skill_key)
                if is_ok:
                    selected_ability = skill_key
                    log.info(f"AIAbilitySelected | actor_id={char_id} ability_key={skill_key}")
                    break

        # 4. Генерация Зон
        all_zones = ["head", "chest", "belly", "legs", "feet"]
        attack_zones = [random.choice(all_zones)]

        # 5 валидных пар
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
        log.info(f"AIActionCalculated | actor_id={char_id} target_id={target_id} ability={selected_ability}")
        return decision
