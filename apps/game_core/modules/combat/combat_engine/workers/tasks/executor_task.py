import contextlib
import time

from loguru import logger as log

from apps.game_core.modules.combat.combat_engine.combat_data_service import CombatDataService
from apps.game_core.modules.combat.combat_engine.processors.executor import CombatExecutor
from apps.game_core.modules.combat.dto.combat_arq_dto import CollectorSignalDTO, WorkerBatchJobDTO
from apps.game_core.modules.combat.dto.combat_internal_dto import CombatActionDTO


async def execute_batch_task(ctx: dict, job_data: dict) -> None:
    """
    Задача Исполнителя (Dispatcher).
    Управляет жизненным циклом обработки батча: Load -> Lock -> Process -> Commit -> Signal.
    """
    try:
        job = WorkerBatchJobDTO(**job_data)
        session_id = job.session_id

        # Получаем сервисы из контекста
        executor: CombatExecutor = ctx["combat_executor"]
        data_service: CombatDataService = ctx.get("combat_data_service")

        if not data_service:
            # Fallback
            if "combat_collector" in ctx:
                data_service = ctx["combat_collector"].data_service
            else:
                log.error("Executor Task | DataService not found")
                return

        # 1. Load Context (Heavy)
        battle_ctx = await data_service.load_battle_context(session_id)
        if not battle_ctx or not battle_ctx.meta.active:
            log.warning(f"Executor Task | Session {session_id} inactive")
            # Снимаем лок на всякий случай (если он был наш)
            await data_service.combat_manager.release_worker_lock_safe(session_id, "unknown")
            return

        # 2. Lock Acquisition (Optimistic)
        my_id = str(time.time())
        locked = await data_service.combat_manager.acquire_worker_lock(session_id, my_id)
        if not locked:
            log.warning(f"Executor Task | Lock busy for {session_id}")
            return

        try:
            # 3. Fetch Actions from Queue
            queue_key = f"combat:rbc:{session_id}:q:actions"
            raw_actions = await data_service.combat_manager.redis.redis_client.lrange(queue_key, 0, job.batch_size - 1)

            if not raw_actions:
                log.info(f"Executor Task | Queue empty for {session_id}")
                return

            actions = []
            for raw in raw_actions:
                with contextlib.suppress(Exception):
                    actions.append(CombatActionDTO.model_validate_json(raw))

            # 4. Process Batch (Pure Logic)
            processed_ids = await executor.process_batch(battle_ctx, actions)

            # 5. Commit (Zombie Check)
            is_mine = await data_service.combat_manager.check_worker_lock(session_id, my_id)
            if not is_mine:
                log.error("Executor Task | Zombie detected! Lock lost. Aborting.")
                return

            await data_service.commit_session(battle_ctx, processed_ids)
            log.info(f"Executor Task | Processed {len(processed_ids)} actions")

        finally:
            # 6. Release Lock
            await data_service.combat_manager.release_worker_lock_safe(session_id, my_id)

            # 7. Heartbeat Signal
            signal = CollectorSignalDTO(session_id=session_id, char_id=0, signal_type="heartbeat", move_id="executor")
            await ctx["redis"].enqueue_job("combat_collector_task", signal.model_dump())

    except Exception as e:
        log.error(f"Executor Task | Error: {e}")
        raise
