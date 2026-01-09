# apps/game_core/modules/combats/session/runtime/combat_turn_manager.py
import time
import uuid
from typing import Any

from loguru import logger as log
from pydantic import ValidationError

from apps.common.core.base_arq import ArqService
from apps.common.schemas_dto.combat_source_dto import CombatMoveDTO, ExchangePayload, InstantPayload, ItemPayload
from apps.common.services.redis.manager.combat_manager import CombatManager
from apps.game_core.modules.combat.dto.combat_arq_dto import CollectorSignalDTO

# Конфиг таймеров согласно документации
AFK_TIMEOUTS = {
    0: 60,  # Обычный ход
    1: 50,
    2: 40,
    3: 30,
}
MIN_TIMEOUT = 20


class CombatTurnManager:
    """
    Постановщик задач (RBC v3.0).
    Управляет буфером намерений и очередями ARQ (Immediate + Delayed).
    """

    def __init__(self, combat_manager: CombatManager, arq_service: ArqService):
        self.combat_manager = combat_manager
        self.arq = arq_service

    async def register_move_request(self, session_id: str, char_id: int, payload: dict[str, Any]) -> None:
        """
        Основной метод регистрации хода.
        Записывает 'пулю' (Intent) и ставит две задачи в ARQ.
        """
        # 1. Определяем тип действия
        action_type = payload.get("action", "attack")

        # 2. Получаем данные персонажа (нужен afk_level для таймера)
        state_dict = await self.combat_manager.get_actor_state(session_id, char_id)

        if not state_dict:
            log.warning(f"TurnManager | Actor {char_id} not found in session {session_id}. Assuming AFK 0.")
            afk_level = 0
        else:
            afk_level = int(state_dict.get("afk_level", 0))

        # 3. Создаем типизированную 'пулю' (DTO)
        try:
            move_dto = self._build_move_dto(char_id, action_type, payload)
        except ValidationError as e:
            log.error(f"TurnManager | Payload validation failed: {e}")
            raise ValueError("Invalid move payload structure") from e

        # 4. Записываем в буфер (Multi-Targeting / Spamming)
        if move_dto.strategy == "exchange":
            target_id = move_dto.payload.get("target_id")
            if not target_id:
                raise ValueError("Target ID is required for exchange")

            success = await self.combat_manager.register_exchange_move_atomic(
                session_id, char_id, int(target_id), move_dto.model_dump()
            )

            if not success:
                raise ValueError("Target is not available in your queue")

        else:
            await self.combat_manager.append_move(session_id, char_id, move_dto.strategy, move_dto.model_dump())

        # 5. РАСЧЕТ ТАЙМЕРА (Force Attack)
        timeout = AFK_TIMEOUTS.get(afk_level, MIN_TIMEOUT)

        # 6. СТАВИМ ДВЕ ЗАДАЧИ В ARQ
        signal_immediate = CollectorSignalDTO(
            session_id=session_id, char_id=char_id, signal_type="check_immediate", move_id=move_dto.move_id
        )
        await self.arq.enqueue_job("combat_collector_task", signal_immediate.model_dump())

        signal_timeout = CollectorSignalDTO(
            session_id=session_id, char_id=char_id, signal_type="check_timeout", move_id=move_dto.move_id
        )
        await self.arq.enqueue_job(
            "combat_collector_task", signal_timeout.model_dump(), _defer_until=int(time.time() + timeout)
        )

        log.info(f"TurnManager | Move {action_type} registered. Strategy: {move_dto.strategy}. Timeout: {timeout}s")

    async def register_moves_batch(self, session_id: str, char_id: int, payloads: list[dict[str, Any]]) -> None:
        """
        Батчевая регистрация ходов (для AI).
        Поддерживает и Exchange (с удалением целей), и Instant/Item (без удаления).
        Ставит таймер Force Attack.
        """
        if not payloads:
            return

        exchange_moves_data = []
        other_moves_dtos = []

        # 1. Build DTOs and Separate
        for payload in payloads:
            action_type = payload.get("action", "attack")
            try:
                move_dto = self._build_move_dto(char_id, action_type, payload)

                if move_dto.strategy == "exchange":
                    target_id = move_dto.payload.get("target_id")
                    if target_id:
                        exchange_moves_data.append(
                            {
                                "move_json": move_dto.model_dump_json(),
                                "target_id": int(target_id),
                                "strategy": move_dto.strategy,
                                "move_id": move_dto.move_id,
                            }
                        )
                else:
                    # Instant / Item
                    other_moves_dtos.append(move_dto)

            except ValidationError:
                continue

        success_count = 0

        # 2. Process Exchange Moves (Atomic Lua with POP)
        if exchange_moves_data:
            count = await self.combat_manager.register_moves_batch_atomic(session_id, char_id, exchange_moves_data)
            success_count += count

        # 3. Process Other Moves (Pipeline without POP)
        if other_moves_dtos:
            await self.combat_manager.append_moves_batch(session_id, char_id, other_moves_dtos)
            success_count += len(other_moves_dtos)

        # 4. Signals (Immediate + Timeout)
        if success_count > 0:
            # A. Immediate
            signal_immediate = CollectorSignalDTO(
                session_id=session_id, char_id=char_id, signal_type="check_immediate", move_id="batch"
            )
            await self.arq.enqueue_job("combat_collector_task", signal_immediate.model_dump())

            # B. Timeout (Force Attack)
            # Ставим один таймер на весь батч (60 сек)
            timeout = 60
            signal_timeout = CollectorSignalDTO(
                session_id=session_id, char_id=char_id, signal_type="check_timeout", move_id="batch"
            )
            await self.arq.enqueue_job(
                "combat_collector_task", signal_timeout.model_dump(), _defer_until=int(time.time() + timeout)
            )

            log.info(f"TurnManager | Batch registered {success_count} moves for {char_id}. Timeout: {timeout}s")
        else:
            log.warning(f"TurnManager | Batch failed or empty for {char_id}")

    def _build_move_dto(self, char_id: int, action: str, data: dict) -> CombatMoveDTO:
        """
        Маппинг входящих данных в правильную стратегию и Payload.
        """
        strategy = "exchange"
        validated_payload = {}

        if action == "use_item":
            strategy = "item"
            validated_payload = ItemPayload(
                item_id=int(data.get("item_id", 0)), target_id=data.get("target_id", char_id)
            )
        elif action in ("use_skill", "cast", "instant"):
            strategy = "instant"
            validated_payload = InstantPayload(
                skill_id=data.get("skill_id", ""), target_id=data.get("target_id", char_id)
            )
        elif action in ("leave", "surrender", "flee"):
            strategy = "system"
            validated_payload = {"sys_action": action}
        else:
            # По умолчанию - боевой размен (attack, defend, etc.)
            strategy = "exchange"
            validated_payload = ExchangePayload(
                target_id=int(data.get("target_id", 0)),
                attack_zones=data.get("attack_zones", []),
                block_zones=data.get("block_zones", []),
                skill_id=data.get("skill_id"),
                item_id=data.get("item_id"),
            )

        return CombatMoveDTO(
            move_id=str(uuid.uuid4())[:8],
            char_id=char_id,
            strategy=strategy,
            payload=validated_payload,  # type: ignore
            created_at=time.time(),
        )
