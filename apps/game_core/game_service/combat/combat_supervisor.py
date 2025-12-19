import asyncio
import json
import time
from typing import NoReturn

from loguru import logger as log
from pydantic import ValidationError

from apps.common.schemas_dto.combat_source_dto import CombatMoveDTO
from apps.common.services.core_service.manager.account_manager import AccountManager
from apps.common.services.core_service.manager.combat_manager import CombatManager
from apps.game_core.game_service.combat.combat_service import CombatService


class CombatSupervisor:
    """
    Актер-надсмотрщик (Supervisor) для системы RBC.
    """

    def __init__(self, session_id: str, combat_manager: CombatManager, account_manager: AccountManager):
        self.session_id = session_id
        self.combat_manager = combat_manager
        self.account_manager = account_manager
        self._is_running = True

    async def run(self) -> NoReturn:
        """
        Главный цикл Актера.
        """
        log.info(f"Supervisor started for session {self.session_id}")

        while self._is_running:
            try:
                actors_ids = await self._get_active_actors()
                if not actors_ids:
                    log.warning(f"Supervisor | No active actors in session {self.session_id}. Stopping.")
                    break

                processed_in_this_cycle = set()
                something_happened = False

                for actor_id in actors_ids:
                    if actor_id in processed_in_this_cycle:
                        continue

                    moves = await self._get_actor_moves(actor_id)

                    for target_id, move_dto in moves.items():
                        if target_id in processed_in_this_cycle:
                            continue

                        is_mutual = await self._check_mutual_target(target_id, actor_id)

                        if is_mutual:
                            await self._process_exchange(actor_id, target_id, is_forced=False)
                            processed_in_this_cycle.add(actor_id)
                            processed_in_this_cycle.add(target_id)
                            something_happened = True
                            break

                        elif self._is_move_expired(move_dto):
                            await self._process_exchange(actor_id, target_id, is_forced=True)
                            processed_in_this_cycle.add(actor_id)
                            processed_in_this_cycle.add(target_id)
                            something_happened = True
                            break

                sleep_time = 0.1 if something_happened else 0.5
                await asyncio.sleep(sleep_time)

            except (OSError, ValueError, KeyError, IndexError) as e:
                log.exception(f"Supervisor caught an exception in session {self.session_id}: {e}")
                await asyncio.sleep(1.0)
        raise asyncio.CancelledError

    async def _get_active_actors(self) -> list[int]:
        """Возвращает ID всех живых участников сессии."""
        actors_json = await self.combat_manager.get_rbc_all_actors_json(self.session_id)
        if not actors_json:
            return []
        return [int(id_str) for id_str in actors_json]

    async def _get_actor_moves(self, actor_id: int) -> dict[int, CombatMoveDTO]:
        """Возвращает словарь ходов игрока."""
        moves_json = await self.combat_manager.get_rbc_moves(self.session_id, actor_id)
        if not moves_json:
            return {}

        moves_dto = {}
        for target_id_str, move_json in moves_json.items():
            try:
                moves_dto[int(target_id_str)] = CombatMoveDTO.model_validate_json(move_json)
            except (ValidationError, json.JSONDecodeError):
                log.warning(f"Invalid move DTO in Redis for {actor_id} -> {target_id_str}")
        return moves_dto

    async def _check_mutual_target(self, actor_a_id: int, actor_b_id: int) -> bool:
        """Проверяет, есть ли у B ход против A."""
        moves_b = await self.combat_manager.get_rbc_moves(self.session_id, actor_b_id)
        return str(actor_a_id) in moves_b if moves_b else False

    def _is_move_expired(self, move_dto: CombatMoveDTO) -> bool:
        """Проверяет поле execute_at < time.now()"""
        return move_dto.execute_at < time.time()

    async def _process_exchange(self, actor_a_id: int, actor_b_id: int, is_forced: bool):
        """
        Обрабатывает обмен, вызывая CombatService.
        """
        log.info(f"Supervisor | Processing exchange {actor_a_id} vs {actor_b_id} (Forced={is_forced})")

        moves_a = await self._get_actor_moves(actor_a_id)
        move_a_dto = moves_a.get(actor_b_id)

        if not move_a_dto:
            log.error(f"Move from {actor_a_id} to {actor_b_id} disappeared.")
            return

        combat_service = CombatService(self.session_id, self.combat_manager, self.account_manager)

        move_a_data = move_a_dto.model_dump()

        if is_forced:
            # Принудительный ход: у второго игрока нет хода, создаем "пассивную защиту"
            move_b_data = {"attack": [], "block": ["head", "chest"], "ability": None}
        else:
            moves_b = await self._get_actor_moves(actor_b_id)
            move_b_dto = moves_b.get(actor_a_id)
            if not move_b_dto:
                log.error(f"Mutual move from {actor_b_id} to {actor_a_id} disappeared.")
                return
            move_b_data = move_b_dto.model_dump()

        await combat_service.process_exchange(actor_a_id, move_a_data, actor_b_id, move_b_data)

        # Очищаем ходы из Redis
        await self.combat_manager.remove_rbc_move(self.session_id, actor_a_id, actor_b_id)
        if not is_forced:
            await self.combat_manager.remove_rbc_move(self.session_id, actor_b_id, actor_a_id)

        # TODO:
        # - Обновить AFK счетчики
        # - Поставить сигнал обновления для клиентов
        # - Убрать из очереди exchanges, если нужно
        log.info(f"Supervisor | Exchange finished for {actor_a_id} vs {actor_b_id}")
