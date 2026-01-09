from loguru import logger as log

from apps.game_core.modules.combat.combat_engine.processors.ai_processor import AiProcessor
from apps.game_core.modules.combat.dto.combat_arq_dto import AiTurnRequestDTO
from apps.game_core.modules.combat.session.runtime.combat_turn_manager import CombatTurnManager


async def ai_turn_task(ctx: dict, request_data: dict) -> None:
    """
    Задача ИИ Агента.
    Делает ход за NPC.
    """
    try:
        request = AiTurnRequestDTO(**request_data)

        turn_manager: CombatTurnManager = ctx["turn_manager"]
        ai_processor: AiProcessor = ctx["ai_processor"]

        targets = request.missing_targets

        if not targets:
            log.warning(f"AI Agent | No targets provided for bot {request.bot_id}")
            return

        payloads = []
        # Атакуем всех из списка
        for target_id in targets:
            # Генерируем решение (зоны)
            payload = ai_processor.decide_exchange(target_id)
            payloads.append(payload)

        # Регистрируем ходы батчем
        if payloads:
            await turn_manager.register_moves_batch(request.session_id, request.bot_id, payloads)

        log.info(f"AI Agent | Bot {request.bot_id} made {len(payloads)} moves (batch)")

    except Exception as e:
        log.error(f"AI Agent | Error: {e}")
        raise
