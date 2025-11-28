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
        actor_dto: CombatSessionContainerDTO,  # 🔥 Теперь принимаем DTO, а не dict
        session_id: str,
    ) -> dict[str, Any]:
        """
        Принимает решение за NPC: кого бить, чем бить и как защищаться.
        """
        char_id = actor_dto.char_id
        my_team = actor_dto.team

        # 1. Получаем список всех участников
        all_ids = await combat_manager.get_session_participants(session_id)

        enemies = []
        threats = []

        for pid in all_ids:
            pid_int = int(pid)
            if pid_int == char_id:
                continue

            raw_target = await combat_manager.get_actor_json(session_id, pid_int)
            if not raw_target:
                continue

            try:
                # Оптимизация: частичный парсинг или full DTO?
                # Для MVP парсим в dict, это быстрее, чем DTO
                target_obj = json.loads(raw_target)
            except json.JSONDecodeError:
                continue

            # Фильтр: Враг и Живой
            hp = target_obj.get("state", {}).get("hp_current", 0)
            if target_obj["team"] != my_team and hp > 0:
                enemies.append(pid_int)

                # Проверяем, не целится ли он в меня
                pending = await combat_manager.get_pending_move(session_id, pid_int, char_id)
                if pending:
                    threats.append(pid_int)

        # 2. Выбор Цели
        target_id = None
        if threats:
            target_id = random.choice(threats)
        elif enemies:
            target_id = random.choice(enemies)
        else:
            return {}

        # 3. Выбор Способности (НОВОЕ)
        selected_ability = None

        # Если у моба есть активные скиллы
        if actor_dto.active_abilities:
            # Перемешиваем, чтобы не бил всегда первым по списку
            shuffled_skills = actor_dto.active_abilities.copy()
            random.shuffle(shuffled_skills)

            for skill_key in shuffled_skills:
                # Проверяем через сервис (хватает ли маны, кулдаун и т.д.)
                is_ok, _ = AbilityService.can_use_ability(actor_dto, skill_key)
                if is_ok:
                    selected_ability = skill_key
                    log.debug(f"AI {char_id} выбрал скилл: {skill_key}")
                    break

        # 4. Генерация Зон
        all_zones = ["head", "chest", "legs", "feet"]
        attack_zones = [random.choice(all_zones)]
        valid_pairs = [
            ["head", "chest"],
            ["chest", "legs"],
            ["legs", "feet"],
            ["feet", "head"],
        ]
        block_zones = random.choice(valid_pairs)

        return {"target_id": target_id, "attack": attack_zones, "block": block_zones, "ability": selected_ability}
