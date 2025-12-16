import json
import random
import time
from typing import Any

from loguru import logger as log

from apps.common.schemas_dto import CombatSessionContainerDTO
from apps.common.services.core_service import CombatManager

BASE_TURN_TIMEOUT = 60
AFK_PENALTY_TIMEOUTS = {
    0: BASE_TURN_TIMEOUT,
    1: 50,
    2: 40,
    3: 30,
    4: 20,
}
VALID_BLOCK_PAIRS = [
    ["head", "chest"],
    ["chest", "belly"],
    ["belly", "legs"],
    ["legs", "feet"],
    ["feet", "head"],
]


class CombatTurnManager:
    """
    Сервис для управления очередностью ходов, регистрацией запросов на ход
    и отслеживанием таймеров в боевой сессии.
    """

    def __init__(self, session_id: str, combat_manager: CombatManager):
        """
        Инициализирует CombatTurnManager.

        Args:
            session_id: Уникальный идентификатор боевой сессии.
            combat_manager: Менеджер боя.
        """
        self.session_id = session_id
        self.combat_manager = combat_manager
        log.debug(f"CombatTurnManager | status=initialized session_id='{self.session_id}'")

    async def register_move_request(
        self,
        actor_id: int,
        target_id: int,
        attack_zones: list[str] | None,
        block_zones: list[str] | None,
        ability_key: str | None,
        actor_dto: CombatSessionContainerDTO,
    ) -> dict[str, Any] | None:
        """
        Регистрирует запрос на ход актора.

        Если находится встречный ход от цели, возвращает данные обоих ходов
        для обработки обмена. Автоматически заполняет зоны атаки/блока
        для AI или при просрочке.

        Args:
            actor_id: Идентификатор актора, совершающего ход.
            target_id: Идентификатор цели хода.
            attack_zones: Список зон, по которым актор атакует.
            block_zones: Список зон, которые актор блокирует.
            ability_key: Ключ способности, используемой актором.
            actor_dto: DTO актора, совершающего ход.

        Returns:
            Словарь, содержащий `my_move` и `enemy_move` (данные ходов обоих акторов),
            если найдена пара ходов. Иначе None.
        """
        log.info(
            f"CombatTurnManager | event=register_move_request actor_id={actor_id} target_id={target_id} session_id='{self.session_id}'"
        )

        if not attack_zones:
            attack_zones = [random.choice(["head", "chest", "belly", "legs", "feet"])]
            log.trace(f"CombatTurnManager | action=autofill_attack_zones actor_id={actor_id}")
        if not block_zones:
            block_zones = random.choice(VALID_BLOCK_PAIRS)
            log.trace(f"CombatTurnManager | action=autofill_block_zones actor_id={actor_id}")

        # Сброс штрафа за АФК при успешном ходе
        if actor_dto.state and actor_dto.state.afk_penalty_level > 0:
            actor_dto.state.afk_penalty_level = 0
            log.debug(f"CombatTurnManager | afk_penalty_reset actor_id={actor_id}")

        # Установка таймаута на основе уровня штрафа
        afk_level = actor_dto.state.afk_penalty_level if actor_dto.state else 0
        timeout = AFK_PENALTY_TIMEOUTS.get(afk_level, 20)  # 20 сек по умолчанию для высоких уровней штрафа

        deadline = int(time.time() + timeout)
        move_data = {
            "target_id": target_id,
            "attack": attack_zones,
            "block": block_zones,
            "ability": ability_key,
            "timestamp": time.time(),
            "deadline": deadline,
        }

        move_json = json.dumps(move_data)
        await self.combat_manager.set_pending_move(self.session_id, actor_id, target_id, move_json, timeout)
        log.debug(
            f"CombatTurnManager | event=pending_move_set actor_id={actor_id} target_id={target_id} session_id='{self.session_id}' timeout={timeout}s"
        )

        counter_move_json = await self.combat_manager.get_pending_move(self.session_id, target_id, actor_id)

        if counter_move_json:
            log.info(
                f"CombatTurnManager | event=move_pair_found actor_a={actor_id} actor_b={target_id} session_id='{self.session_id}'"
            )
            await self.combat_manager.delete_pending_move(self.session_id, actor_id, target_id)
            await self.combat_manager.delete_pending_move(self.session_id, target_id, actor_id)
            log.debug(
                f"CombatTurnManager | action=pending_moves_cleaned pair={actor_id},{target_id} session_id='{self.session_id}'"
            )

            try:
                return {"my_move": move_data, "enemy_move": json.loads(counter_move_json)}
            except json.JSONDecodeError:
                log.exception(
                    f"CombatTurnManager | status=failed reason='Counter move JSON decode error' actor_id={target_id} target_id={actor_id} session_id='{self.session_id}'"
                )
                return None

        log.debug(
            f"CombatTurnManager | event=no_counter_move actor_id={actor_id} target_id={target_id} session_id='{self.session_id}'"
        )
        return None

    async def check_expired_deadlines(self, actors_map: dict[int, CombatSessionContainerDTO]) -> list[tuple[int, int]]:
        """
        Проверяет все ожидающие ходы на предмет истечения таймера.
        При нахождении просроченного хода, увеличивает `afk_penalty_level` у "ленивого" игрока.

        Args:
            actors_map: Словарь, где ключ — ID актора, а значение — его DTO.

        Returns:
            Список кортежей `(lazy_actor_id, opponent_id)` для всех просроченных ходов.
            `lazy_actor_id` — это актор, который не сделал ход вовремя.
        """
        expired_pairs: list[tuple[int, int]] = []
        now = time.time()
        log.trace(
            f"CombatTurnManager | event=check_deadlines session_id='{self.session_id}' actors_count={len(actors_map)}"
        )

        for actor_id, actor_dto in actors_map.items():
            if not actor_dto or not actor_dto.state or not actor_dto.state.targets:
                continue

            target_id = actor_dto.state.targets[0]
            pending_json = await self.combat_manager.get_pending_move(self.session_id, actor_id, target_id)

            if pending_json:
                try:
                    data = json.loads(pending_json)
                    if 0 < data.get("deadline", 0) < now:
                        lazy_actor_id = target_id
                        expired_pairs.append((lazy_actor_id, actor_id))

                        # Наказание за АФК
                        lazy_actor_dto = actors_map.get(lazy_actor_id)
                        if lazy_actor_dto and lazy_actor_dto.state:
                            lazy_actor_dto.state.afk_penalty_level = min(4, lazy_actor_dto.state.afk_penalty_level + 1)
                            log.warning(
                                f"CombatTurnManager | afk_penalty_increase lazy_actor={lazy_actor_id} new_level={lazy_actor_dto.state.afk_penalty_level}"
                            )
                            await self.combat_manager.save_actor_json(
                                self.session_id, lazy_actor_id, lazy_actor_dto.model_dump_json()
                            )

                        log.warning(
                            f"CombatTurnManager | event=deadline_expired lazy_actor={lazy_actor_id} waiting_actor={actor_id} session_id='{self.session_id}'"
                        )
                except json.JSONDecodeError:
                    log.exception(
                        f"CombatTurnManager | status=failed reason='Pending move JSON decode error' actor_id={actor_id} target_id={target_id} session_id='{self.session_id}'"
                    )

        return expired_pairs
