import asyncio
import time
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.schemas_dto.combat_source_dto import (
    ActorSnapshotDTO,
    CombatDashboardDTO,
    CombatMoveDTO,
    CombatSessionContainerDTO,
    FighterStateDTO,
    StatSourceData,
)
from apps.common.services.core_service.manager.account_manager import AccountManager
from apps.common.services.core_service.manager.combat_manager import CombatManager
from apps.common.services.core_service.redis_key import RedisKeys as Rk
from apps.game_core.game_service.combat.combat_lifecycle_service import CombatLifecycleService
from apps.game_core.game_service.combat.combat_service import CombatService
from apps.game_core.game_service.combat.combat_supervisor import CombatSupervisor
from apps.game_core.game_service.combat.stats_calculator import StatsCalculator
from apps.game_core.game_service.combat.supervisor_manager import add_supervisor_task


class CombatOrchestratorRBC:
    """
    Оркестратор боевой системы (RBC).
    Отвечает за:
    1. Инициализацию боя и запуск Актера-надсмотрщика.
    2. Регистрацию ходов игрока в Redis (запись "пуль").
    3. Предоставление данных клиенту (какая цель следующая).
    """

    def __init__(
        self,
        session: AsyncSession,
        combat_manager: CombatManager,
        account_manager: AccountManager,
    ):
        self.session = session
        self.combat_manager = combat_manager
        self.account_manager = account_manager
        self.lifecycle_service = CombatLifecycleService(combat_manager, account_manager)

    async def start_battle(self, players: list[int], enemies: list[int]) -> CombatDashboardDTO:
        """
        Создает боевую сессию, запускает Supervisor'а и возвращает стартовый Snapshot.
        """
        session_id = str(uuid.uuid4())

        # 1. Инициализация участников
        participants = {char_id: "blue" for char_id in players}
        participants.update({char_id: "red" for char_id in enemies})

        for char_id, team in participants.items():
            await self.lifecycle_service.add_participant(self.session, session_id, char_id, team, f"Fighter {char_id}")

        await self.lifecycle_service.initialize_battle_state(session_id)

        # 2. Наполнение очереди обменов через ключи из RedisKeys
        for player_id in players:
            queue_key = Rk.get_combat_exchanges_key(session_id, player_id)
            await self.combat_manager.redis_service.push_to_list(queue_key, *[str(eid) for eid in enemies])

        # 3. Создание метаданных (ставим active=1)
        await self.combat_manager.create_session_meta(
            session_id, {"start_time": str(time.time()), "active": "1", "mode": "rbc"}
        )

        # 4. Запуск Supervisor
        supervisor = CombatSupervisor(session_id, self.combat_manager)
        task = asyncio.create_task(supervisor.run())
        add_supervisor_task(session_id, task)

        # 5. Возвращаем Snapshot для инициатора (первого в списке)
        return await self.get_dashboard_snapshot(session_id, players[0])

    async def register_move(
        self, session_id: str, char_id: int, target_id: int, move_data: dict[str, Any]
    ) -> CombatDashboardDTO:
        """Регистрирует ход и возвращает Snapshot (уже со следующей целью из очереди)."""
        actor_state_json = await self.combat_manager.get_rbc_actor_state_json(session_id, char_id)

        if actor_state_json:
            actor_state = FighterStateDTO.model_validate_json(actor_state_json)

            penalty = getattr(actor_state, "penalty_timer", 60)
            execute_at = int(time.time()) + penalty

            move_dto = CombatMoveDTO(
                target_id=target_id,
                attack_zones=move_data.get("attack_zones", []),
                block_zones=move_data.get("block_zones", []),
                ability_key=move_data.get("ability_key"),
                execute_at=execute_at,
            )

            await self.combat_manager.register_rbc_move(session_id, char_id, target_id, move_dto.model_dump_json())
            await self.combat_manager.pop_from_exchange_queue(session_id, char_id)

        return await self.get_dashboard_snapshot(session_id, char_id)

    async def use_consumable(self, session_id: str, char_id: int, item_id: int) -> tuple[bool, str]:
        """
        Использует расходуемый предмет в бою.
        """
        service = CombatService(session_id, self.combat_manager, self.account_manager)
        return await service.use_consumable(char_id, item_id)

    async def switch_target(self, session_id: str, char_id: int, new_target_id: int) -> tuple[bool, str]:
        """
        Изменяет текущую цель для атакующего актора.
        """
        service = CombatService(session_id, self.combat_manager, self.account_manager)
        return await service.switch_target(char_id, new_target_id)

    async def get_next_target(self, session_id: str, char_id: int) -> dict[str, Any] | None:
        """
        Возвращает следующую цель для атаки.
        """
        active_moves = await self.combat_manager.get_rbc_moves(session_id, char_id)
        if active_moves:
            return None

        target_id = await self.combat_manager.get_rbc_next_target_id(session_id, char_id)

        if not target_id:
            return None

        target_state_json = await self.combat_manager.get_rbc_actor_state_json(session_id, target_id)

        if not target_state_json:
            return None

        target_state = FighterStateDTO.model_validate_json(target_state_json)

        return {
            "char_id": target_id,
            "hp_current": target_state.hp_current,
        }

    async def get_full_state(self, session_id: str, char_id: int) -> dict[str, Any]:
        """
        Собирает ПОЛНОЕ состояние боя для отрисовки интерфейса.
        """
        all_actors_json = await self.combat_manager.get_rbc_all_actors_json(session_id)

        player_state = None
        enemies_state = []

        if all_actors_json:
            for actor_id_str, actor_json in all_actors_json.items():
                actor_id = int(actor_id_str)
                state = FighterStateDTO.model_validate_json(actor_json)

                if actor_id == char_id:
                    player_state = state
                else:
                    enemies_state.append(state)

        return {
            "session_id": session_id,
            "player": player_state,
            "enemies": enemies_state,
            "logs": await self.get_logs(session_id),
        }

    async def get_logs(self, session_id: str, limit: int = 10) -> list[str]:
        """
        Возвращает последние N записей из лога боя.
        """
        return await self.combat_manager.get_combat_log_list(session_id)

    async def check_battle_status(self, session_id: str) -> str:
        """
        Проверяет, не закончился ли бой (победа/поражение).
        """
        return "active"

    async def get_dashboard_snapshot(self, session_id: str, char_id: int) -> CombatDashboardDTO:
        """
        Собирает облегченный Snapshot данных для Бота.
        Это единственный метод, который Бот будет дергать для получения состояния.
        """
        # 1. Метаданные (активен ли бой)
        meta = await self.combat_manager.get_session_meta(session_id)
        if not meta:
            raise ValueError(f"Session meta not found for session {session_id}")
        is_active = int(meta.get("active", 1)) == 1
        status = "active" if is_active else "finished"
        winner = meta.get("winner")

        # 2. Состояние всех бойцов
        all_actors_raw = await self.combat_manager.get_rbc_all_actors_json(session_id)
        if not all_actors_raw:
            raise ValueError(f"No actors found for session {session_id}")

        snapshots: dict[int, ActorSnapshotDTO] = {}
        player_team = "blue"

        for aid_str, raw_json in all_actors_raw.items():
            aid = int(aid_str)
            container = CombatSessionContainerDTO.model_validate_json(raw_json)

            # Считаем Максимумы прямо в Ядре (StatsCalculator)
            hp_max = int(StatsCalculator.calculate("hp_max", container.stats.get("hp_max", StatSourceData(base=100))))
            en_max = int(
                StatsCalculator.calculate("energy_max", container.stats.get("energy_max", StatSourceData(base=100)))
            )

            snapshots[aid] = ActorSnapshotDTO(
                char_id=aid,
                name=container.name,
                hp_current=container.state.hp_current if container.state else 0,
                hp_max=hp_max,
                energy_current=container.state.energy_current if container.state else 0,
                energy_max=en_max,
                team=container.team,
                is_dead=bool(container.state and container.state.hp_current <= 0),
                effects=list(container.state.effects.keys()) if container.state else [],
                tokens=container.state.tokens if container.state else {},
            )
            if aid == char_id:
                player_team = container.team

        # 3. Очередь и Текущая цель
        queue_len = await self.combat_manager.get_rbc_queue_length(session_id, char_id)
        target_id = await self.combat_manager.get_rbc_next_target_id(session_id, char_id)

        # 4. Проверка статуса "Ожидание" (если пуля уже в Redis)
        if is_active:
            moves = await self.combat_manager.get_rbc_moves(session_id, char_id)
            if moves:
                status = "waiting"

        player_snap = snapshots.get(char_id)
        if not player_snap:
            # Обработка ошибки, если игрока нет в сессии
            raise ValueError(f"Player {char_id} not found in session {session_id}")

        return CombatDashboardDTO(
            session_id=session_id,
            status=status,
            player=player_snap,
            current_target=snapshots.get(target_id) if target_id else None,
            enemies=[s for s in snapshots.values() if s.team != player_team],
            allies=[s for s in snapshots.values() if s.team == player_team and s.char_id != char_id],
            queue_count=queue_len,
            switch_charges=player_snap.tokens.get("tactics", 0),
            last_logs=await self.get_logs(session_id),
            winner_team=winner,
        )
