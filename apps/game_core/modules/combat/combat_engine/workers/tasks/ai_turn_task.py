from loguru import logger as log

from apps.game_core.modules.combat.combat_engine.processors.ai_processor import AiProcessor
from apps.game_core.modules.combat.dto.combat_arq_dto import AiTurnRequestDTO
from apps.game_core.modules.combat.session.runtime.combat_turn_manager import CombatTurnManager


async def ai_turn_task(ctx: dict, request_data: dict) -> None:
    """
    Задача ИИ Агента (AI Agent).

    Принимает решение за NPC (монстров) и регистрирует их действия в системе.
    Выполняется асинхронно, чтобы тяжелые алгоритмы (Minimax/BehaviorTree)
    не блокировали основной цикл боя.

    Args:
        ctx: Контекст ARQ.
        request_data: Данные запроса (AiTurnRequestDTO).
    """
    try:
        request = AiTurnRequestDTO(**request_data)

        turn_manager: CombatTurnManager = ctx["turn_manager"]
        ai_processor: AiProcessor = ctx["ai_processor"]

        targets = request.missing_targets

        if not targets:
            log.warning(
                "AiTurnSkip | reason=no_targets bot_id={bot_id} session_id={session_id}",
                bot_id=request.bot_id,
                session_id=request.session_id,
            )
            return

        payloads = []
        # Атакуем всех из списка (One-to-Many logic)
        for target_id in targets:
            # Core Logic: Принятие решения
            payload = ai_processor.decide_exchange(target_id)
            payloads.append(payload)

        # Register Moves (Batch Write)
        if payloads:
            await turn_manager.register_moves_batch(request.session_id, request.bot_id, payloads)

        log.info(
            "AiTurnSuccess | session_id={session_id} bot_id={bot_id} moves={count}",
            session_id=request.session_id,
            bot_id=request.bot_id,
            count=len(payloads),
        )

    except Exception:
        log.exception("AiTurnError | bot_id={bot_id}", bot_id=request_data.get("bot_id", "unknown"))
        raise
