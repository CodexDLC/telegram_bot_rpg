# app/services/game_service/combat/combat_turn_manager.py
import json
import random
import time

from loguru import logger as log

from app.resources.schemas_dto.combat_source_dto import CombatSessionContainerDTO
from app.services.core_service.manager.combat_manager import combat_manager

# Константы
TURN_TIMEOUT = 60
VALID_BLOCK_PAIRS = [
    ["head", "chest"],
    ["chest", "belly"],
    ["belly", "legs"],
    ["legs", "feet"],
    ["feet", "head"],  # "Раскорячка" / Акробат / Сальто
]


class CombatTurnManager:
    """Отвечает за регистрацию ходов, таймеры и валидацию очереди."""

    def __init__(self, session_id: str):
        """
        Args:
            session_id: Идентификатор сессии боя.
        """
        self.session_id = session_id
        log.debug(f"CombatTurnManagerInit | session_id={self.session_id}")

    async def register_move_request(
        self,
        actor_id: int,
        target_id: int,
        attack_zones: list[str] | None,
        block_zones: list[str] | None,
        ability_key: str | None,
    ) -> dict | None:
        """
        Регистрирует ход. Если есть встречный ход — возвращает его данные.

        Args:
            actor_id: ID атакующего.
            target_id: ID цели.
            attack_zones: Зоны атаки.
            block_zones: Зоны блока.
            ability_key: Ключ способности.

        Returns:
            Словарь с данными обоих ходов или None.
        """
        log.info(f"RegisterMoveRequest | actor_id={actor_id} target_id={target_id} session_id={self.session_id}")
        # Авто-заполнение (если манекен или тайм-аут)
        if not attack_zones:
            attack_zones = [random.choice(["head", "chest", "legs", "feet"])]
            log.trace(f"AutoFill | type=attack_zones actor_id={actor_id}")
        if not block_zones:
            block_zones = random.choice(VALID_BLOCK_PAIRS)
            log.trace(f"AutoFill | type=block_zones actor_id={actor_id}")

        deadline = int(time.time() + TURN_TIMEOUT)
        move_data = {
            "target_id": target_id,
            "attack": attack_zones,
            "block": block_zones,
            "ability": ability_key,
            "timestamp": time.time(),
            "deadline": deadline,
        }

        # 1. Сохраняем "Я атакую Его"
        move_json = json.dumps(move_data)
        await combat_manager.set_pending_move(self.session_id, actor_id, target_id, move_json)
        log.debug(f"PendingMoveSet | actor_id={actor_id} target_id={target_id} session_id={self.session_id}")

        # 2. Проверяем "Он атакует Меня?"
        counter_move_json = await combat_manager.get_pending_move(self.session_id, target_id, actor_id)

        if counter_move_json:
            log.info(f"MovePairFound | actor_a={actor_id} actor_b={target_id} session_id={self.session_id}")
            # Есть пара! Можно считать раунд.
            await combat_manager.delete_pending_move(self.session_id, actor_id, target_id)
            await combat_manager.delete_pending_move(self.session_id, target_id, actor_id)
            log.debug(f"PendingMovesCleaned | pair={actor_id},{target_id} session_id={self.session_id}")

            try:
                return {"my_move": move_data, "enemy_move": json.loads(counter_move_json)}
            except json.JSONDecodeError:
                log.exception(
                    f"CounterMoveParseFail | actor_id={target_id} target_id={actor_id} session_id={self.session_id}",
                    exc_info=True,
                )
                return None

        log.debug(f"NoCounterMove | actor_id={actor_id} target_id={target_id} session_id={self.session_id}")
        return None

    async def check_expired_deadlines(self, actors_map: dict[int, CombatSessionContainerDTO]) -> list[tuple[int, int]]:
        """
        Проверяет просроченные ходы.

        Args:
            actors_map: Словарь с DTO участников.

        Returns:
            Список пар (кто_просрочил, на_кого_нападал).
        """
        expired_pairs: list[tuple[int, int]] = []
        now = time.time()
        log.trace(f"CheckExpiredDeadlines | session_id={self.session_id} actors_count={len(actors_map)}")

        for actor_id, actor_dto in actors_map.items():
            if not actor_dto or not actor_dto.state or not actor_dto.state.targets:
                continue

            target_id = actor_dto.state.targets[0]
            pending_json = await combat_manager.get_pending_move(self.session_id, actor_id, target_id)

            if pending_json:
                try:
                    data = json.loads(pending_json)
                    if 0 < data.get("deadline", 0) < now:
                        # Тот, КТО НЕ СХОДИЛ (target), должен получить принудительный ход
                        expired_pairs.append((target_id, actor_id))
                        log.warning(
                            f"DeadlineExpiredFound | lazy_actor={target_id} waiting_actor={actor_id} session_id={self.session_id}"
                        )
                except json.JSONDecodeError:
                    log.error(
                        f"DeadlineCheckParseFail | actor_id={actor_id} target_id={target_id} session_id={self.session_id}",
                        exc_info=True,
                    )

        return expired_pairs
