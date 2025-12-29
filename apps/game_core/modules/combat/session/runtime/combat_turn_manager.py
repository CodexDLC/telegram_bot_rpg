import random
import time
from typing import Any

from loguru import logger as log

from apps.common.schemas_dto import CombatMoveDTO, CombatSessionContainerDTO
from apps.common.services.core_service import CombatManager
from apps.common.services.core_service.manager.account_manager import AccountManager
from apps.game_core.modules.combat.supervisor.task_dispatcher import CombatTaskDispatcherProtocol

# Стандартные пары блоков для 1h/dual
VALID_BLOCK_PAIRS = ["head_chest", "chest_belly", "belly_legs", "legs_feet", "feet_head"]
# Одинарные блоки для 2h
VALID_SINGLE_BLOCKS = ["head", "chest", "belly", "legs", "feet"]

# Таймауты в зависимости от уровня штрафа цели
AFK_TIMEOUTS = {
    0: 60,
    1: 50,
    2: 40,
    3: 30,
}
MIN_TIMEOUT = 20


class CombatTurnManager:
    """
    Сервис для обработки ходов (RBC Architecture).
    Отвечает за валидацию, формирование DTO хода и постановку в очередь Redis.
    """

    def __init__(
        self,
        combat_manager: CombatManager,
        account_manager: AccountManager,
        task_dispatcher: CombatTaskDispatcherProtocol,  # Инъекция диспетчера
    ):
        self.combat_manager = combat_manager
        self.account_manager = account_manager
        self.task_dispatcher = task_dispatcher

    async def register_move_request(
        self,
        session_id: str,
        char_id: int,
        move_data: dict[str, Any],
    ) -> None:
        """
        Регистрирует ход игрока.
        """
        # 1. Загружаем актора (себя)
        raw_actor = await self.combat_manager.get_rbc_actor_state_json(session_id, char_id)
        if not raw_actor:
            log.error(f"TurnManager | Actor {char_id} not found in session {session_id}")
            return

        actor_dto = CombatSessionContainerDTO.model_validate_json(raw_actor)

        # Сброс штрафа за АФК
        if actor_dto.state and actor_dto.state.afk_penalty_level > 0:
            actor_dto.state.afk_penalty_level = 0
            await self.combat_manager.set_rbc_actor_state_json(session_id, char_id, actor_dto.model_dump_json())
            log.info(f"TurnManager | AFK penalty reset for {char_id}")

        # 2. Определяем Layout оружия
        layout = self._determine_weapon_layout(actor_dto)

        # 3. Валидация и Автозаполнение
        attack_zones = self._validate_attacks(move_data.get("attack_zones"), layout)
        block_zones = self._validate_blocks(move_data.get("block_zones"), layout)

        # 4. Определяем цель (из очереди)
        target_id = await self.combat_manager.get_rbc_next_target_id(session_id, char_id)
        if not target_id:
            log.warning(f"TurnManager | No target in queue for {char_id}. Move ignored.")
            return

        # 5. Расчет таймаута
        timeout = 60
        raw_target = await self.combat_manager.get_rbc_actor_state_json(session_id, target_id)
        if raw_target:
            try:
                target_dto = CombatSessionContainerDTO.model_validate_json(raw_target)
                if target_dto.state:
                    penalty = target_dto.state.afk_penalty_level
                    timeout = AFK_TIMEOUTS.get(penalty, MIN_TIMEOUT)
            except Exception:  # noqa: BLE001
                pass

        execute_at = int(time.time() + timeout)

        # 6. Формируем DTO
        move_dto = CombatMoveDTO(
            target_id=target_id,
            attack_zones=attack_zones,
            block_zones=block_zones,
            ability_key=move_data.get("ability_key"),
            execute_at=execute_at,
        )

        # 7. Сохраняем в Redis
        await self.combat_manager.register_rbc_move(session_id, char_id, target_id, move_dto.model_dump_json())

        # 8. Убираем цель из очереди
        await self.combat_manager.pop_from_exchange_queue(session_id, char_id)

        log.info(f"TurnManager | Move registered: {char_id} -> {target_id} (Timeout: {timeout}s)")

        # 9. Запускаем проверку (через диспетчер)
        # Это абстракция: сейчас это Local Task, потом будет ARQ Job
        await self.task_dispatcher.dispatch_check(session_id)

    def _determine_weapon_layout(self, actor: CombatSessionContainerDTO) -> str:
        """Определяет тип раскладки: '1h', 'dual', '2h'."""
        has_offhand = False
        is_2h = False

        for item in actor.equipped_items:
            if item.item_type.value != "weapon":
                continue

            # Check if slot exists and is off_hand
            if hasattr(item, "slot") and item.slot == "off_hand":
                has_offhand = True
            # Check if slot exists and is main_hand, and subtype is 2h
            elif (
                hasattr(item, "slot")
                and item.slot == "main_hand"
                and item.subtype in ("melee_2h", "ranged_2h", "staff")
            ):
                is_2h = True

        if is_2h:
            return "2h"
        if has_offhand:
            return "dual"
        return "1h"

    def _validate_attacks(self, input_zones: list[str] | None, layout: str) -> list[str]:
        zones = input_zones or []
        required_count = 2 if layout == "dual" else 1
        available_zones = ["head", "chest", "belly", "legs", "feet"]

        while len(zones) < required_count:
            choice = random.choice(available_zones)
            if layout == "dual" and choice in zones and len(available_zones) > 1:
                continue
            zones.append(choice)

        if len(zones) > required_count:
            zones = zones[:required_count]
        return zones

    def _validate_blocks(self, input_zones: list[str] | None, layout: str) -> list[str]:
        raw_zones = input_zones or []
        if not raw_zones:
            raw_zones = [random.choice(VALID_SINGLE_BLOCKS)] if layout == "2h" else [random.choice(VALID_BLOCK_PAIRS)]

        final_zones = []
        for z in raw_zones:
            if "_" in z:
                parts = z.split("_")
                final_zones.extend(parts)
            else:
                final_zones.append(z)
        return final_zones
