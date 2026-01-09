from apps.common.core.base_arq import ArqService, BaseArqSettings, base_shutdown, base_startup
from apps.common.services.redis.manager.combat_manager import CombatManager
from apps.game_core.modules.combat.combat_engine.combat_data_service import CombatDataService
from apps.game_core.modules.combat.combat_engine.processors.ai_processor import AiProcessor
from apps.game_core.modules.combat.combat_engine.processors.collector import CombatCollector
from apps.game_core.modules.combat.combat_engine.processors.executor import CombatExecutor
from apps.game_core.modules.combat.session.runtime.combat_turn_manager import CombatTurnManager

from .tasks.ai_turn_task import ai_turn_task
from .tasks.chaos_task import chaos_check_task

# Импорты тасок
from .tasks.collector_task import combat_collector_task
from .tasks.executor_task import execute_batch_task


async def combat_startup(ctx):
    """
    Инициализация боевого воркера.
    """
    # 1. Базовая инициализация (Redis)
    await base_startup(ctx)

    # 2. Инициализация боевых сервисов
    redis_service = ctx["redis_service"]

    combat_manager = CombatManager(redis_service)
    data_service = CombatDataService(combat_manager)

    # ArqService для TurnManager
    arq_service = ArqService()

    # 3. Инициализация менеджеров
    turn_manager = CombatTurnManager(combat_manager, arq_service)

    # 4. Инициализация процессоров
    ctx["combat_data_service"] = data_service  # Важно для Executor Task
    ctx["combat_collector"] = CombatCollector(data_service)
    ctx["combat_executor"] = CombatExecutor()  # Чистый процессор
    ctx["ai_processor"] = AiProcessor()

    ctx["turn_manager"] = turn_manager
    ctx["arq_service_internal"] = arq_service


async def combat_shutdown(ctx):
    """Очистка ресурсов."""
    if "arq_service_internal" in ctx:
        await ctx["arq_service_internal"].close()
    await base_shutdown(ctx)


class CombatArqSettings(BaseArqSettings):
    """
    Настройки ARQ воркера для боевой системы.
    """

    # Оптимизация под высокий темп
    max_jobs = 50
    job_timeout = 30
    keep_result = 0

    on_startup = combat_startup
    on_shutdown = combat_shutdown

    # Список задач (функций), которые выполняет этот воркер
    functions = [combat_collector_task, execute_batch_task, ai_turn_task, chaos_check_task]
