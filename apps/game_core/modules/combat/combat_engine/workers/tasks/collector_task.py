from loguru import logger as log

from apps.game_core.modules.combat.combat_engine.combat_data_service import CombatDataService
from apps.game_core.modules.combat.combat_engine.processors.collector import CombatCollector
from apps.game_core.modules.combat.dto.combat_arq_dto import CollectorSignalDTO, WorkerBatchJobDTO


async def combat_collector_task(ctx: dict, signal_data: dict) -> None:
    """
    Задача Коллектора (Matchmaker).
    Триггерится при каждом ходе игрока или по таймауту.
    """
    try:
        signal = CollectorSignalDTO(**signal_data)

        collector: CombatCollector = ctx["combat_collector"]
        data_service: CombatDataService = collector.data_service

        # 1. Запускаем логику сбора и матчмейкинга
        # Передаем signal для обработки Force Attack
        batch_size, ai_tasks = await collector.collect_actions(signal.session_id, signal)

        # 2. Dispatch AI Tasks
        if ai_tasks:
            for task in ai_tasks:
                await ctx["redis"].enqueue_job("ai_turn_task", task.model_dump())
            log.info(f"Collector | Dispatched {len(ai_tasks)} AI tasks for {signal.session_id}")

        # 3. Dispatch Executor Task (с проверкой лока)
        if batch_size > 0:
            # Проверяем, свободна ли сессия, и если да - ставим флаг "задача в очереди"
            can_enqueue = await data_service.combat_manager.check_and_lock_busy_for_collector(signal.session_id)

            if can_enqueue:
                job_dto = WorkerBatchJobDTO(session_id=signal.session_id, batch_size=batch_size)
                await ctx["redis"].enqueue_job("execute_batch_task", job_dto.model_dump())
                log.info(f"Collector | Dispatched Executor for {signal.session_id} (batch={batch_size})")
            else:
                log.info(f"Collector | Executor is busy for {signal.session_id}, skipping enqueue.")

    except Exception as e:
        log.error(f"Collector | Error: {e}")
        raise
