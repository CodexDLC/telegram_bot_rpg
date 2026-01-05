# apps/game_core/modules/combat/supervisor/combat_supervisor.py
import asyncio
import time
from typing import Any

from loguru import logger as log

from apps.common.services.core_service.manager.account_manager import AccountManager
from apps.common.services.core_service.manager.combat_manager import CombatManager
from apps.common.services.core_service.manager.context_manager import ContextRedisManager
from apps.game_core.modules.combat.mechanics.combat_service import CombatExchangeOrchestrator
from apps.game_core.modules.combat.supervisor.combat_supervisor_manager import remove_supervisor_task


class CombatSupervisor:
    """
    Наблюдатель за боевой сессией.
    Отвечает за:
    1. Мониторинг очереди ходов (поиск пар).
    2. Отслеживание таймаутов (AFK).
    3. Запуск механики (CombatService) для обработки раунда.

    Архитектура:
    - Stateless Logic: Метод `process_tick` содержит всю логику одной итерации.
    - Stateful Runner: Метод `run` крутит цикл (для локального запуска).
    """

    def __init__(
        self,
        session_id: str,
        combat_manager: CombatManager,
        account_manager: AccountManager,
        context_manager: ContextRedisManager,
    ):
        self.session_id = session_id
        self.combat_manager = combat_manager
        self.account_manager = account_manager
        self.context_manager = context_manager
        self._running = True

    async def run(self):
        """
        Основной цикл (для Local Asyncio).
        В ARQ архитектуре этот метод не нужен, будет вызываться process_tick напрямую.
        """
        log.info(f"Supervisor | Started for session {self.session_id}")

        try:
            while self._running:
                # 1. Выполняем одну итерацию логики
                should_continue = await self.process_tick()

                if not should_continue:
                    break

                # 2. Пауза (Polling interval)
                # В ARQ этого не будет, там событийная модель.
                await asyncio.sleep(1.0)

        except asyncio.CancelledError:
            log.info(f"Supervisor | Cancelled for session {self.session_id}")
        except Exception as e:  # noqa: BLE001
            log.exception(f"Supervisor | Error in session {self.session_id}: {e}")
        finally:
            # Очистка при выходе
            remove_supervisor_task(self.session_id)
            log.info(f"Supervisor | Stopped for session {self.session_id}")

    async def process_tick(self) -> bool:
        """
        Одна итерация проверки состояния боя.
        Возвращает True, если нужно продолжать наблюдение, False — если бой окончен.

        Этот метод готов к переносу в ARQ Worker.
        """
        # 1. Distributed Lock (Защита от гонки)
        # Используем Redis Lock, чтобы два воркера (или два тика) не обработали одну сессию одновременно.
        # lock_key = f"lock:combat:{self.session_id}"
        # async with self.combat_manager.redis_service.lock(lock_key, timeout=5):
        #     return await self._process_logic()

        # Пока у нас нет удобного метода lock в redis_service, делаем без него (для монолита ок).
        # Но структуру закладываем.
        return await self._process_logic()

    async def _process_logic(self) -> bool:
        """Внутренняя логика тика (под локом)."""

        # 1. Проверка активности боя
        meta = await self.combat_manager.get_rbc_session_meta(self.session_id)
        if not meta or meta.get("active") != "1":
            log.info(f"Supervisor | Session {self.session_id} finished or not found. Stopping.")
            return False

        # 2. Загрузка пуль (Moves)
        # Нам нужно проверить, есть ли пары ходов (Target A -> B и Target B -> A)
        # Это сложная проверка, так как пули лежат в разных ключах combat:rbc:{sid}:moves:{aid}

        # Получаем всех участников
        actors_map = await self.combat_manager.get_rbc_all_actors_json(self.session_id)
        if not actors_map:
            return False

        actor_ids = [int(aid) for aid in actors_map]

        # Ищем пары
        # TODO: Оптимизация - не перебирать всех, если их 100.
        # Но для 2-4 игроков это мгновенно.

        processed_any = False

        for actor_id in actor_ids:
            # Читаем пули этого актора (кого он бьет)
            moves_dict = await self.combat_manager.get_rbc_moves(self.session_id, actor_id)
            if not moves_dict:
                continue

            for target_id_str, move_json in moves_dict.items():
                target_id = int(target_id_str)

                # Проверяем встречную пулю (Target -> Actor)
                counter_moves = await self.combat_manager.get_rbc_moves(self.session_id, target_id)

                if counter_moves and str(actor_id) in counter_moves:
                    # ПАРА НАЙДЕНА! (A->B и B->A)
                    log.info(f"Supervisor | Match found: {actor_id} <-> {target_id}")

                    # Вызываем механику
                    service = CombatExchangeOrchestrator(
                        self.session_id, self.combat_manager, self.account_manager, self.context_manager
                    )

                    # Parse JSON moves to dicts
                    import json

                    move_a = json.loads(move_json)
                    move_b = json.loads(counter_moves[str(actor_id)])

                    await service.process_exchange(actor_id, move_a, target_id, move_b)

                    processed_any = True
                    # После обмена пули удаляются внутри process_exchange (или должны удаляться)
                    # Важно: process_exchange должен удалить пули из Redis!
                    # TODO: Ensure process_exchange or caller removes moves.
                    # For now, let's assume CombatService handles cleanup or we do it here.
                    # Ideally, CombatService should handle it to be atomic.
                    # But if not, we should remove them here:
                    await self.combat_manager.remove_rbc_move(self.session_id, actor_id, target_id)
                    await self.combat_manager.remove_rbc_move(self.session_id, target_id, actor_id)

        # 3. Проверка таймаутов (AFK)
        # Если пар нет, проверяем, не протухли ли одиночные пули
        if not processed_any:
            await self._check_timeouts(actor_ids)

        return True

    async def _check_timeouts(self, actor_ids: list[int]):
        """Проверяет просроченные пули и форсирует обмен."""
        now = time.time()

        for actor_id in actor_ids:
            moves_dict = await self.combat_manager.get_rbc_moves(self.session_id, actor_id)
            if not moves_dict:
                continue

            for target_id_str, move_json in moves_dict.items():
                # Парсим пулю, чтобы узнать дедлайн
                # (В идеале дедлайн можно хранить в отдельном поле, чтобы не парсить JSON)
                import json

                try:
                    move_data = json.loads(move_json)
                    execute_at = move_data.get("execute_at", 0)

                    if execute_at > 0 and now > execute_at:
                        target_id = int(target_id_str)
                        log.warning(f"Supervisor | Timeout expired for pair {actor_id}->{target_id}")

                        # Форсируем обмен (Враг не ответил)
                        # Генерируем заглушку для врага
                        service = CombatExchangeOrchestrator(
                            self.session_id, self.combat_manager, self.account_manager, self.context_manager
                        )

                        # Since process_timeout_exchange is missing, we simulate a dummy move for the target
                        # or implement process_timeout_exchange in CombatService.
                        # Assuming we need to implement logic here or call a method that handles it.
                        # Let's construct a dummy move for the target (AFK move)
                        dummy_move: dict[str, Any] = {
                            "attack_zones": [],
                            "block_zones": [],
                            "ability": None,
                            "is_afk": True,
                        }

                        await service.process_exchange(actor_id, move_data, target_id, dummy_move)

                        # Remove moves
                        await self.combat_manager.remove_rbc_move(self.session_id, actor_id, target_id)

                except Exception as e:  # noqa: BLE001
                    log.error(f"Supervisor | Error checking timeout: {e}")
