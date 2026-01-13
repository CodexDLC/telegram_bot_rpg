from typing import Any

from apps.game_core.modules.combat.dto.combat_internal_dto import BattleMeta, CombatActionDTO
from loguru import logger as log

from apps.common.schemas_dto.combat_source_dto import CombatMoveDTO
from apps.game_core.modules.combat.combat_engine.combat_data_service import CombatDataService
from apps.game_core.modules.combat.combat_engine.logic.target_resolver import TargetResolver
from apps.game_core.modules.combat.dto.combat_arq_dto import AiTurnRequestDTO, CollectorSignalDTO


class CombatCollector:
    """
    Коллектор (Collector Processor).
    Отвечает за сбор намерений (Moves), матчмейкинг и формирование задач для Исполнителя.
    Цикл: Load Snapshot -> Logic (AI, Instant, Exchange) -> Batch Save -> Return Tasks.
    """

    def __init__(self, data_service: CombatDataService):
        self.data_service = data_service
        self.target_resolver = TargetResolver()

    async def collect_actions(
        self, session_id: str, signal: CollectorSignalDTO | None = None
    ) -> tuple[int, list[AiTurnRequestDTO]]:
        """
        Основной метод коллектора.
        Возвращает:
        - batch_size (int): Рекомендуемый размер батча для Исполнителя (0, если действий нет).
        - ai_tasks (List[AiTurnRequestDTO]): Список задач для AI агентов.
        """
        # 1. Load Snapshot (Meta + Moves + Targets)
        meta = await self.data_service.get_battle_meta(session_id)
        if not meta or not meta.active:
            return 0, []

        # Получаем список всех участников из Meta
        all_actor_ids = []
        for team_ids in meta.teams.values():
            all_actor_ids.extend(team_ids)

        # Грузим мувы всех участников
        moves_map = await self.data_service.get_intent_moves(session_id, all_actor_ids)

        # Грузим очереди целей (для AI)
        targets_map = await self.data_service.get_targets(session_id)

        # 2. Logic Processing
        actions_to_queue: list[CombatActionDTO] = []
        ai_tasks: list[AiTurnRequestDTO] = []

        # A. AI Check (с учетом целей)
        ai_tasks = self._check_ai_turns(session_id, meta, moves_map, targets_map)

        # B. Instant Harvesting (Items/Skills)
        instants, del_inst = self._harvest_instant(moves_map, meta)
        actions_to_queue.extend(instants)

        # C. Exchange Matchmaking (Combat + Force Attack)
        exchanges, del_exch = self._matchmake_exchange(moves_map, signal)
        actions_to_queue.extend(exchanges)

        # 3. Batch Save (Push Actions + Delete Moves)
        if actions_to_queue:
            # Атомарный перенос (Push + Delete)
            await self.data_service.transfer_actions(session_id, actions_to_queue)

        # 4. Calculate Batch Size (Dynamic)
        batch_size = 0
        if actions_to_queue:
            actors_count = len(all_actor_ids)
            # Формула: Чем больше актеров, тем меньше батч (чтобы не перегрузить воркер загрузкой контекста)
            # Base: 200. Min: 5. Max: 100.
            batch_size = min(100, max(5, int(200 / max(1, actors_count))))

        return batch_size, ai_tasks

    def _check_ai_turns(
        self, session_id: str, meta: BattleMeta, moves_map: dict[int, Any], targets_map: dict[int, list[int]]
    ) -> list[AiTurnRequestDTO]:
        """
        Проверяет, кто из AI еще не сделал ход.
        Сравнивает очередь целей (targets) с заявленными мувами (exchange).
        """
        tasks = []

        for actor_id_str, actor_type in meta.actors_info.items():
            if actor_type != "ai":
                continue

            if not actor_id_str.lstrip("-").isdigit():
                continue

            actor_id = int(actor_id_str)

            # 1. Получаем цели бота
            my_targets = targets_map.get(actor_id, [])
            if not my_targets:
                continue  # Нет целей - нет проблем (или бот спит)

            # 2. Получаем заявленные Exchange мувы
            actor_moves = moves_map.get(actor_id, {})
            exchange_moves = actor_moves.get("exchange", {})

            covered_targets = set()
            for move_json in exchange_moves.values():
                try:
                    # Парсим JSON, чтобы достать target_id
                    move = CombatMoveDTO(**move_json)
                    tid = move.payload.get("target_id")
                    if tid:
                        covered_targets.add(int(tid))
                except Exception:  # noqa: BLE001
                    pass

            # 3. Сравниваем
            missing_targets = list(set(my_targets) - covered_targets)

            if missing_targets:
                # Бот не покрыл все цели -> Ставим задачу с указанием целей
                tasks.append(AiTurnRequestDTO(session_id=session_id, bot_id=actor_id, missing_targets=missing_targets))

        return tasks

    def _harvest_instant(self, moves_map: dict[int, Any], meta: BattleMeta) -> tuple[list[CombatActionDTO], list[str]]:
        """Собирает Instant и Item мувы, резолвит цели."""
        actions = []
        to_delete = []

        for char_id, moves_data in moves_map.items():
            if not moves_data:
                continue

            # Объединяем обработку Item и Instant, так как логика таргетинга похожа
            for strategy in ["item", "instant"]:
                moves_dict = moves_data.get(strategy, {})

                for move_id, move_json in moves_dict.items():
                    try:
                        move = CombatMoveDTO(**move_json)

                        # Резолвинг целей через TargetResolver
                        target_ids = self.target_resolver.resolve(char_id, move.payload.get("target_id"), meta)

                        # Записываем результат резолвинга в сам мув
                        move.targets = target_ids

                        # Создаем ОДИН Action на весь мув (с множеством целей)
                        action = CombatActionDTO(action_type=strategy, move=move, is_forced=False)
                        actions.append(action)
                        to_delete.append(move_id)  # Удаляем мув после обработки

                    except Exception as e:  # noqa: BLE001
                        log.error(f"Collector | Failed to parse {strategy} move {move_id}: {e}")

        return actions, to_delete

    def _matchmake_exchange(
        self, moves_map: dict[int, Any], signal: CollectorSignalDTO | None = None
    ) -> tuple[list[CombatActionDTO], list[str]]:
        """Ищет пары для обмена ударами. Обрабатывает Force Attack по таймауту."""
        actions = []
        to_delete = []

        # Простой перебор (O(N^2) в худшем случае, но N мал)
        # Собираем пул всех exchange заявок
        pool = []
        for _char_id, moves_data in moves_map.items():
            exchanges = moves_data.get("exchange", {})
            for _move_id, move_json in exchanges.items():
                try:
                    move = CombatMoveDTO(**move_json)
                    pool.append(move)
                except Exception:  # noqa: BLE001
                    pass

        # Сортируем по времени (FIFO)
        pool.sort(key=lambda x: x.created_at)

        matched_ids = set()

        # 1. Normal Matchmaking
        for move_a in pool:
            if move_a.move_id in matched_ids:
                continue

            target_id = move_a.payload.get("target_id")
            if not target_id:
                continue
            target_id = int(target_id)

            # Ищем ответный мув (B -> A)
            for move_b in pool:
                if move_b.move_id in matched_ids:
                    continue
                if move_b.char_id != target_id:
                    continue

                # Проверяем, бьет ли B игрока A
                target_b = int(move_b.payload.get("target_id", 0))
                if target_b == move_a.char_id:
                    # ПАРА НАЙДЕНА!
                    action = CombatActionDTO(action_type="exchange", move=move_a, partner_move=move_b, is_forced=False)
                    actions.append(action)
                    matched_ids.add(move_a.move_id)
                    matched_ids.add(move_b.move_id)
                    to_delete.append(move_a.move_id)
                    to_delete.append(move_b.move_id)
                    break

        # 2. Force Attack Check (Timeout)
        if signal and signal.signal_type == "check_timeout" and signal.move_id:
            # Ищем мув, который вызвал таймаут
            # Если он еще в пуле (не сматчился выше) -> Force Attack

            # Если move_id="batch", мы не знаем конкретный ID.
            # Но для AI мы ставим "batch".
            # Значит, если "batch", мы должны проверить ВСЕ мувы AI?
            # Или просто пройтись по всем оставшимся в пуле и проверить их возраст?
            # Давайте пока поддержим конкретный ID и "batch" (как Force All Old).

            force_candidates = []

            if signal.move_id == "batch":
                # Force all unmatched moves for this char_id (if provided)
                # Signal содержит char_id.
                for move in pool:
                    if move.move_id not in matched_ids and move.char_id == signal.char_id:
                        force_candidates.append(move)
            else:
                # Specific move
                for move in pool:
                    if move.move_id == signal.move_id and move.move_id not in matched_ids:
                        force_candidates.append(move)
                        break

            for move in force_candidates:
                # Создаем Force Action (односторонний)
                action = CombatActionDTO(
                    action_type="exchange",  # Или "forced"? Оставим exchange, но is_forced=True
                    move=move,
                    partner_move=None,  # Нет партнера
                    is_forced=True,
                )
                actions.append(action)
                matched_ids.add(move.move_id)
                to_delete.append(move.move_id)
                log.warning(f"Collector | Force Attack triggered for {move.move_id}")

        return actions, to_delete
