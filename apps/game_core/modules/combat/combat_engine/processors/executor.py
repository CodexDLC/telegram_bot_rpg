import asyncio

from loguru import logger as log

from apps.game_core.modules.combat.combat_engine.logic.combat_pipeline import CombatPipeline
from apps.game_core.modules.combat.dto.combat_internal_dto import BattleContext, CombatActionDTO


class CombatExecutor:
    """
    Исполнитель (Executor Processor).
    Чистая бизнес-логика обработки батча действий.
    Управляет потоком выполнения (Flow Control), делегируя расчеты в Pipeline.
    """

    def __init__(self):
        self.pipeline = CombatPipeline()

    async def process_batch(self, ctx: BattleContext, actions: list[CombatActionDTO]) -> list[str]:
        """
        Обрабатывает список действий, изменяя BattleContext in-place.
        Возвращает список ID успешно обработанных действий.
        """
        processed_ids = []

        for action in actions:
            try:
                await self._process_single_action(ctx, action)
                processed_ids.append(action.move.move_id)
            except Exception as e:  # noqa: BLE001
                log.error(f"Executor | Action {action.move.move_id} failed: {e}")
                # Считаем обработанным (чтобы удалить из очереди), но с ошибкой
                processed_ids.append(action.move.move_id)

        return processed_ids

    async def _process_single_action(self, ctx: BattleContext, action: CombatActionDTO) -> None:
        """
        Обработка одного действия.
        Точка входа и маршрутизации (Routing).
        """
        if not action.move:
            log.warning("Executor | Action has no move data")
            return

        # Routing Logic
        # Exchange (Дуэль) или Forced Attack (Односторонний удар по манекену)
        # Forced Attack обрабатывается в ветке Exchange, так как это физическое взаимодействие
        if action.action_type == "exchange" or (action.is_forced and action.move.payload.get("target_id")):
            await self._handle_exchange(ctx, action)
        else:
            # Instant / Item (Одностороннее воздействие на N целей)
            await self._handle_unidirectional(ctx, action)

    # ==========================================================================
    # 🌿 BRANCHES (Logic Flow)
    # ==========================================================================

    async def _handle_exchange(self, ctx: BattleContext, action: CombatActionDTO) -> None:
        """
        Ветка: Обмен ударами (Exchange).
        Может быть 2 задачи (A->B, B->A) или 1 задача (A->B, если Forced).
        """
        source = ctx.get_actor(action.move.char_id)
        target_id = action.move.payload.get("target_id")
        target = ctx.get_actor(int(target_id)) if target_id else None

        if not source or not target:
            log.warning(f"Executor | Exchange participants not found: {action.move.char_id} -> {target_id}")
            return

        tasks = []

        # --- PHASE 1: INTERFERENCE CHECK (Предварительная проверка) ---
        # TODO: Вызвать InterferenceService.resolve(action.move, action.partner_move)
        # 1. Проверить наличие флагов контроля (Stun, Knockdown) в интентах.
        # 2. Если есть конфликт -> Сравнить инициативу.
        # 3. Сгенерировать external_mods (дебаффы) для проигравшего.

        # mods_for_source = {} # Заглушка (удалено, так как не используется)
        # mods_for_target = {} # Заглушка (удалено, так как не используется)

        # --- PHASE 2: TASK GENERATION (A -> B) ---
        # TODO: Multi-Hit Logic
        # 1. Проверить триггер "Dual Wield" (шанс удара второй рукой).
        # 2. Проверить триггер "Double Strike" (абилка).
        # 3. Если сработало -> Добавить в tasks НЕСКОЛЬКО вызовов pipeline.

        # Task 1: Main Hand (Всегда)
        # ВАЖНО: Pipeline пока синхронный, поэтому оборачиваем в to_thread или делаем async
        # Пока вызываем синхронно, но сохраняем структуру tasks для будущего async

        # tasks.append(self.pipeline.calculate(source, target, action.move, mods=mods_for_source))
        self.pipeline.calculate(source, target, action.move)

        # Task 2: Off Hand (Optional)
        # if dual_wield_proc:
        #     tasks.append(self.pipeline.calculate(source, target, action.move, mods=mods_for_source, hand="off"))

        # --- PHASE 3: TASK GENERATION (B -> A) ---
        if action.partner_move:
            # Аналогичная логика для второго участника
            # Task 1: Main Hand
            # tasks.append(self.pipeline.calculate(target, source, action.partner_move, mods=mods_for_target))
            self.pipeline.calculate(target, source, action.partner_move)
        elif not action.is_forced:
            log.error("Executor | Exchange action without partner and not forced")
            return

        # --- PHASE 4: EXECUTION ---
        if tasks:
            await asyncio.gather(*tasks)

    async def _handle_unidirectional(self, ctx: BattleContext, action: CombatActionDTO) -> None:
        """
        Ветка: Одностороннее действие (Instant / Item).
        Инициатор воздействует на список целей.
        """
        source = ctx.get_actor(action.move.char_id)
        if not source:
            return

        # Цели уже резолвлены Коллектором и лежат в action.move.targets
        target_ids = action.move.targets or []

        tasks = []
        for tid in target_ids:
            target = ctx.get_actor(tid)
            if target:
                # tasks.append(self.pipeline.calculate(source, target, action.move))
                self.pipeline.calculate(source, target, action.move)
            elif action.move.strategy == "item" and action.move.payload.get("target_id") == "self":
                # Self-cast (если target_id не резолвился в список int)
                self.pipeline.calculate(source, source, action.move)

        if tasks:
            await asyncio.gather(*tasks)
