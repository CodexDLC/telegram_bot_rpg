import time

from loguru import logger as log

from apps.game_core.modules.combat.combat_engine.combat_data_service import CombatDataService
from apps.game_core.modules.combat.combat_engine.logic.chaos_service import ChaosService


async def chaos_check_task(ctx: dict, session_id: str) -> None:
    """
    Задача Хаоса (Garbage Collector / Event).
    Работает по принципу эстафеты: проверяет активность и ставит себя же через 5 минут.
    """
    try:
        # Инициализация сервисов (если их нет в ctx, создаем, но лучше брать из ctx)
        # В combat_arq.py мы не положили ChaosService в ctx.
        # Но у нас есть combat_manager.

        # Получаем сервисы из контекста (или создаем на лету, если нет)
        # В combat_arq.py мы создали data_service.
        data_service: CombatDataService = ctx.get(
            "combat_data_service"
        )  # В combat_arq.py мы не положили его под этим ключом?
        # В combat_arq.py: ctx['combat_collector'] = CombatCollector(data_service)
        # Мы можем достать data_service из коллектора или создать новый.
        # Лучше добавить data_service в ctx в combat_arq.py.

        # Fallback:
        if not data_service:
            # Пытаемся достать из коллектора
            if "combat_collector" in ctx:
                data_service = ctx["combat_collector"].data_service
            else:
                # Если совсем беда, выходим (или создаем, но нужен redis_service)
                log.error("Chaos | DataService not found in context")
                return

        # ChaosService создаем на лету (он легкий)
        chaos_service = ChaosService(data_service.combat_manager)

        # 1. Загружаем мету
        meta = await data_service.get_battle_meta(session_id)
        if not meta or not meta.active:
            # Сессия закрыта или не существует -> Эстафета прерывается
            # log.debug(f"Chaos | Session {session_id} inactive, stopping relay")
            return

        # 2. Считаем простой: Delta = Now - LastActivity
        now = int(time.time())
        delta = now - meta.last_activity_at

        if delta > 600:  # 10 минут тишины
            # Время вышло — Мусорщик приходит за ними
            spawned = await chaos_service.spawn_cleaner(session_id)
            if spawned:
                log.info(f"Chaos | Cleaner spawned in {session_id} (delta={delta}s)")
            else:
                # Уже заспавнен
                pass

        # 3. ПЕРЕДАЕМ ЭСТАФЕТУ (Рекурсия через ARQ)
        # Ставим следующую проверку через 5 минут (300 сек)
        await ctx["redis"].enqueue_job("chaos_check_task", session_id, _defer_until=int(time.time() + 300))

    except Exception as e:
        log.error(f"Chaos | Error: {e}")
        # Если ошибка, эстафета может прерваться.
        # Можно попробовать перезапустить, но лучше не спамить ошибками.
        raise
