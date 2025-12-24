import time

from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.services.core_service import CombatManager
from apps.common.services.core_service.manager.account_manager import AccountManager
from apps.common.services.core_service.manager.arena_manager import ArenaManager
from apps.game_core.game_service.arena.matchmaking_service import MatchmakingService
from apps.game_core.game_service.combat.combat_orchestrator_rbc import CombatOrchestratorRBC


class Arena1v1Service:
    """
    Сервис для управления 1v1 боями на арене.
    """

    def __init__(
        self,
        session: AsyncSession,
        char_id: int,
        arena_manager: ArenaManager,
        combat_manager: CombatManager,
        account_manager: AccountManager,
    ):
        self.session = session
        self.char_id = char_id
        self.mm_service = MatchmakingService(session, account_manager)
        self.mode = "1v1"
        self.arena_manager = arena_manager
        self.combat_manager = combat_manager

        # Оставляем только RBC Оркестратор
        self.rbc_orchestrator = CombatOrchestratorRBC(session, combat_manager, account_manager)
        log.debug(f"Arena1v1Service | status=initialized char_id={char_id}")

    async def join_queue(self) -> int:
        """Постановка в очередь."""
        await self.combat_manager.delete_player_status(self.char_id)
        gs = await self.mm_service.get_cached_gs(self.char_id)
        await self.arena_manager.add_to_queue(self.mode, self.char_id, float(gs))
        meta = {"start_time": time.time(), "gs": gs}
        await self.arena_manager.create_request(self.char_id, meta)
        log.info(f"Arena1v1 | event=joined_queue char_id={self.char_id} gs={gs}")
        return gs

    async def check_and_match(self, attempt: int = 1) -> str | None:
        """
        Проверяет наличие активного боя или ищет противника в очереди.
        """
        active_session = await self._check_active_battle()
        if active_session:
            return active_session

        my_req = await self.arena_manager.get_request(self.char_id)
        if not my_req:
            return None

        my_gs = my_req["gs"]
        range_pct = min(0.30, 0.05 * attempt)
        min_score = my_gs * (1.0 - range_pct)
        max_score = my_gs * (1.0 + range_pct)

        candidates = await self.arena_manager.get_candidates(self.mode, min_score, max_score)

        opponent_id = None
        for c_id_str in candidates:
            c_id = int(c_id_str)
            if c_id != self.char_id:
                opponent_id = c_id
                break

        if not opponent_id:
            return None

        is_removed = await self.arena_manager.remove_from_queue(self.mode, opponent_id)
        if not is_removed:
            return None

        await self.arena_manager.remove_from_queue(self.mode, self.char_id)
        await self.arena_manager.delete_request(self.char_id)
        await self.arena_manager.delete_request(opponent_id)

        session_id = await self._create_pvp_battle(opponent_id)
        return session_id

    async def cancel_queue(self) -> None:
        """
        Удаляет персонажа из очереди на арену и удаляет его заявку.
        """
        await self.arena_manager.remove_from_queue(self.mode, self.char_id)
        await self.arena_manager.delete_request(self.char_id)
        log.info(f"Arena1v1 | event=queue_cancelled char_id={self.char_id}")

    async def _create_pvp_battle(self, opponent_id: int) -> str:
        """Создает PvP бой через единую точку входа RBC."""
        dashboard_dto = await self.rbc_orchestrator.start_battle(
            players=[self.char_id], enemies=[opponent_id], config={"battle_type": "pvp", "mode": self.mode}
        )
        session_id = dashboard_dto.session_id

        await self._set_player_status(self.char_id, session_id)
        await self._set_player_status(opponent_id, session_id)

        log.info(f"Arena1v1 | event=pvp_battle_started session_id={session_id}")
        return session_id

    async def create_shadow_battle(self) -> str:
        """Создает бой с Тенью."""
        await self.cancel_queue()

        dashboard_dto = await self.rbc_orchestrator.start_battle(
            players=[self.char_id], config={"battle_type": "arena_shadow", "mode": self.mode}
        )
        session_id = dashboard_dto.session_id

        await self._set_player_status(self.char_id, session_id)
        log.info(f"Arena1v1 | event=shadow_battle_started session_id={session_id}")
        return session_id

    async def _check_active_battle(self) -> str | None:
        """
        Проверяет, участвует ли персонаж уже в активном бою.
        """
        val = await self.combat_manager.get_player_status(self.char_id)
        if val and val.startswith("combat:"):
            return val.split(":")[1]
        return None

    async def _set_player_status(self, char_id: int, session_id: str) -> None:
        """
        Устанавливает статус игрока в Redis.
        """
        await self.combat_manager.set_player_status(char_id, f"combat:{session_id}", ttl=600)
        log.debug(f"Arena1v1 | event=player_status_set char_id={char_id} status='combat:{session_id}'")
