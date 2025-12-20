import asyncio
import json
import time
from typing import NoReturn

from loguru import logger as log

from apps.common.schemas_dto import CombatSessionContainerDTO
from apps.common.schemas_dto.combat_source_dto import CombatMoveDTO
from apps.common.services.core_service.manager.account_manager import AccountManager
from apps.common.services.core_service.manager.combat_manager import CombatManager
from apps.game_core.game_service.combat.mechanics.combat_ai_service import CombatAIService
from apps.game_core.game_service.combat.mechanics.combat_service import CombatService

# Конфиг воркера
MOVE_TIMEOUT = 60  # Тот самый отчет в 60 секунд
TICK_DELAY = 0.5  # Частота проверки состояния боя


class CombatSupervisor:
    """
    Supervisor RBC. Заставляет ботов ходить и следит за таймерами.
    """

    def __init__(self, session_id: str, combat_manager: CombatManager, account_manager: AccountManager):
        self.session_id = session_id
        self.combat_manager = combat_manager
        self.account_manager = account_manager
        self.ai_service = CombatAIService(combat_manager)
        self._is_running = True

    async def run(self) -> NoReturn:
        log.info(f"Supervisor [RBC] started | session='{self.session_id}'")

        while self._is_running:
            try:
                # 1. Получаем метаданные сессии (Single Source of Truth)
                meta = await self.combat_manager.get_rbc_session_meta(self.session_id)
                if not meta or int(meta.get("active", 0)) == 0:
                    log.info(f"Supervisor | Session {self.session_id} inactive. Exiting.")
                    break

                # Парсим данные из меты
                try:
                    teams = json.loads(meta.get("teams", "{}"))
                    actors_info = json.loads(meta.get("actors_info", "{}"))
                    dead_actors = set(json.loads(meta.get("dead_actors", "[]")))
                except json.JSONDecodeError:
                    log.error(f"Supervisor | Meta parse error session_id='{self.session_id}'")
                    await asyncio.sleep(1.0)
                    continue

                # 2. Проверка условия победы
                if await self._check_win_condition(teams, dead_actors):
                    break

                # 3. Получаем все активные ходы ("пули")
                # В текущей реализации RedisService нет метода get_all_moves_in_session,
                # поэтому придется итерироваться по живым участникам.
                # Оптимизация: в будущем можно сделать HGETALL combat:rbc:{id}:all_moves

                # Собираем все ходы
                all_moves: dict[int, dict[int, CombatMoveDTO]] = {}
                active_ids = [int(aid) for aid in actors_info if int(aid) not in dead_actors]

                for actor_id in active_ids:
                    moves = await self._get_actor_moves(actor_id)
                    if moves:
                        all_moves[actor_id] = moves

                processed_pairs = set()

                for actor_id in active_ids:
                    # --- ЛОГИКА AI: Создание угрозы ---
                    # Если это AI, он жив и у него нет активных ходов -> генерируем ход
                    if actors_info.get(str(actor_id)) == "ai" and actor_id not in all_moves:
                        # Проверяем, есть ли у бота уже запланированные ходы
                        # Для генерации хода нам нужен DTO, но мы договорились не грузить всех.
                        # Придется загрузить только этого бота.
                        container = await self._get_actor(actor_id)
                        if container:
                            await self._ensure_ai_move(container)

                    # --- ЛОГИКА ОБМЕНОВ: Поиск пар или таймаутов ---
                    if actor_id not in all_moves:
                        continue

                    moves = all_moves[actor_id]
                    for target_id, move_dto in moves.items():
                        pair = tuple(sorted((actor_id, target_id)))
                        if pair in processed_pairs:
                            continue

                        # Сценарий А: Взаимный ход (Оба походили)
                        # Проверяем, есть ли у цели ход на нас
                        is_mutual = False
                        if target_id in all_moves and actor_id in all_moves[target_id]:
                            is_mutual = True

                        # Сценарий Б: Таймаут (Игрок ушел спать, или моб просрочен)
                        is_expired = move_dto.execute_at < time.time()

                        if is_mutual or is_expired:
                            await self._execute_exchange(actor_id, target_id, is_forced=is_expired and not is_mutual)
                            processed_pairs.add(pair)

                await asyncio.sleep(TICK_DELAY)

            except Exception as e:  # noqa: BLE001
                log.exception(f"Supervisor Error | {self.session_id} | {e}")
                await asyncio.sleep(1.0)

        raise asyncio.CancelledError

    async def _check_win_condition(self, teams: dict[str, list[int]], dead_actors: set[int]) -> bool:
        """
        Проверяет, не закончился ли бой.
        Если одна из команд полностью мертва -> вызывает finish_battle.
        """
        alive_teams = []
        for team_name, members in teams.items():
            # Если хотя бы один член команды жив (не в dead_actors) -> команда жива
            if any(m for m in members if m not in dead_actors):
                alive_teams.append(team_name)

        # Если осталась 1 или 0 команд -> конец
        if len(alive_teams) <= 1:
            winner = alive_teams[0] if alive_teams else "draw"
            service = CombatService(self.session_id, self.combat_manager, self.account_manager)
            await service.lifecycle_service.finish_battle(self.session_id, winner)
            return True

        return False

    async def _ensure_ai_move(self, actor_dto: CombatSessionContainerDTO):
        """Проверяет наличие хода у моба, если нет - создает (угроза)."""
        # Достаем цель из очереди обменов (может быть None)
        target_id = await self.combat_manager.get_rbc_next_target_id(self.session_id, actor_dto.char_id)

        # Генерируем решение через AI Service (он сам найдет цель, если target_id=None)
        decision = await self.ai_service.calculate_action(actor_dto, self.session_id, target_id)

        final_target_id = decision.get("target_id")
        if not final_target_id:
            return

        move_dto = CombatMoveDTO(
            target_id=final_target_id,
            attack_zones=decision.get("attack", []),
            block_zones=decision.get("block", ["head", "chest"]),
            ability_key=decision.get("ability"),
            execute_at=int(time.time() + MOVE_TIMEOUT),  # Ставим дедлайн
        )

        await self.combat_manager.register_rbc_move(
            self.session_id, actor_dto.char_id, final_target_id, move_dto.model_dump_json()
        )
        log.debug(f"Supervisor | AI Move Created (Threat): {actor_dto.char_id} -> {final_target_id}")

    async def _execute_exchange(self, id_a: int, id_b: int, is_forced: bool):
        """Проводит расчет обмена."""
        service = CombatService(self.session_id, self.combat_manager, self.account_manager)

        # Данные хода A всегда берем из Redis
        moves_a = await self._get_actor_moves(id_a)
        move_a = moves_a.get(id_b)

        # Данные хода B: либо из Redis, либо "пассив", если принудительно по таймауту
        if is_forced:
            # Если A походил, а B - нет, и время вышло: B должен сделать случайный ход
            log.warning(f"Supervisor | Forced Exchange (Timeout): {id_a} vs {id_b}")

            # Загружаем DTO для B, чтобы AI мог сгенерировать ход
            actor_b_dto = await self._get_actor(id_b)

            if actor_b_dto:
                # Генерируем случайный ход через AI Service
                # Передаем id_a как цель, чтобы AI знал, кого бить в ответ
                decision = await self.ai_service.calculate_action(actor_b_dto, self.session_id, target_id=id_a)

                move_b_data = {
                    "target_id": id_a,
                    "attack_zones": decision.get("attack", []),
                    "block_zones": decision.get("block", ["head", "chest"]),
                    "ability": decision.get("ability"),
                    "execute_at": int(time.time()),
                }
            else:
                # Fallback, если не удалось загрузить актора (крайний случай)
                move_b_data = {
                    "target_id": id_a,
                    "attack_zones": [],
                    "block_zones": ["head", "chest"],
                    "ability": None,
                    "execute_at": int(time.time()),
                }
        else:
            moves_b = await self._get_actor_moves(id_b)
            move_b = moves_b.get(id_a)
            move_b_data = move_b.model_dump() if move_b else {}

        if move_a:
            await service.process_exchange(id_a, move_a.model_dump(), id_b, move_b_data)

        # Чистим пули
        await self.combat_manager.remove_rbc_move(self.session_id, id_a, id_b)
        if not is_forced:
            await self.combat_manager.remove_rbc_move(self.session_id, id_b, id_a)

    async def _get_actor(self, aid: int):
        data = await self.combat_manager.get_rbc_actor_state_json(self.session_id, aid)
        return CombatSessionContainerDTO.model_validate_json(data) if data else None

    async def _get_actor_moves(self, aid: int) -> dict[int, CombatMoveDTO]:
        raw = await self.combat_manager.get_rbc_moves(self.session_id, aid)
        res = {}
        if raw:
            for tid, m_json in raw.items():
                try:
                    res[int(tid)] = CombatMoveDTO.model_validate_json(m_json)
                except Exception:  # noqa: BLE001
                    continue
        return res
