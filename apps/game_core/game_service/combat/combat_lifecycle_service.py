import asyncio
import json
import time
import uuid
from datetime import date
from typing import Any

from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.database.repositories import (
    get_character_stats_repo,
    get_skill_progress_repo,
    get_skill_rate_repo,
)
from apps.common.database.session import async_session_factory
from apps.common.schemas_dto import (
    CombatSessionContainerDTO,
    FighterStateDTO,
    StatSourceData,
)
from apps.common.services.core_service import CombatManager
from apps.common.services.core_service.manager.account_manager import AccountManager
from apps.game_core.game_service.analytics.analytics_service import analytics_service
from apps.game_core.game_service.combat.combat_aggregator import CombatAggregator
from apps.game_core.game_service.combat.stats_calculator import StatsCalculator
from apps.game_core.game_service.skill.skill_service import CharacterSkillsService

SWITCH_CHARGES_BASE = 1
SWITCH_CHARGES_PER_ENEMY = 0.5
SWITCH_CHARGES_CAP_MULTIPLIER = 5


class CombatLifecycleService:
    """
    Сервис управления жизненным циклом боевых сессий.

    Отвечает за создание, инициализацию, добавление участников и завершение боя,
    включая распределение опыта и сохранение состояния персонажей.
    """

    def __init__(self, combat_manager: CombatManager, account_manager: AccountManager):
        self.combat_manager = combat_manager
        self.account_manager = account_manager

    async def create_battle(self, is_pve: bool = True, mode: str = "world") -> str:
        """
        Создает новую боевую сессию.

        Args:
            is_pve: Флаг, указывающий, является ли бой PvE (True) или PvP (False).
            mode: Режим боя (например, "arena", "dungeon", "world"),
                  определяет логику выхода из боя.

        Returns:
            Уникальный идентификатор созданной боевой сессии.
        """
        session_id = str(uuid.uuid4())
        meta_data: dict[str, Any] = {
            "start_time": int(time.time()),
            "is_pve": int(is_pve),
            "active": 1,
            "mode": mode,
        }
        await self.combat_manager.create_session_meta(session_id, meta_data)
        log.info(f"CombatLifecycle | event=battle_created session_id='{session_id}' is_pve={is_pve} mode='{mode}'")
        return session_id

    async def add_participant(
        self, session: AsyncSession, session_id: str, char_id: int, team: str, name: str, is_ai: bool = False
    ) -> None:
        """
        Добавляет реального игрока или полноценного NPC в боевую сессию.

        Инициализирует состояние участника с полным HP/Energy.

        Args:
            session: Асинхронная сессия базы данных.
            session_id: Идентификатор боевой сессии.
            char_id: Идентификатор персонажа-участника.
            team: Команда участника (например, "blue", "red").
            name: Имя участника.
            is_ai: Флаг, указывающий, является ли участник AI.
        """
        log.info(
            f"CombatLifecycle | event=add_participant session_id='{session_id}' char_id={char_id} name='{name}' team='{team}' is_ai={is_ai}"
        )
        aggregator = CombatAggregator(session, self.account_manager)
        container = await aggregator.collect_session_container(char_id)
        container.team, container.name, container.is_ai = team, name, is_ai

        final_stats = StatsCalculator.aggregate_all(container.stats)
        current_hp = int(final_stats.get("hp_max", 100))
        current_energy = int(final_stats.get("energy_max", 40))

        container.state = FighterStateDTO(
            hp_current=current_hp,
            energy_current=current_energy,
            targets=[],
            switch_charges=0,
            max_switch_charges=0,
            xp_buffer={},
        )

        await self.combat_manager.add_participant_id(session_id, char_id)
        await self.combat_manager.save_actor_json(session_id, char_id, container.model_dump_json())
        log.debug(f"CombatLifecycle | event=participant_added session_id='{session_id}' char_id={char_id}")

    async def add_dummy_participant(self, session_id: str, char_id: int, hp: int, energy: int, name: str) -> None:
        """
        Добавляет "манекен" или "тень" в боевую сессию с заданными параметрами.

        Используется для создания AI-противников, не имеющих полной базы данных.

        Args:
            session_id: Идентификатор боевой сессии.
            char_id: Идентификатор персонажа-манекена.
            hp: Начальное количество HP манекена.
            energy: Начальное количество Energy манекена.
            name: Имя манекена.
        """
        log.info(
            f"CombatLifecycle | event=add_dummy_participant session_id='{session_id}' char_id={char_id} name='{name}'"
        )
        container = CombatSessionContainerDTO(char_id=char_id, team="red", name=name, is_ai=True)
        container.state = FighterStateDTO(
            hp_current=hp, energy_current=energy, targets=[], switch_charges=0, max_switch_charges=0, xp_buffer={}
        )
        container.stats["hp_max"] = StatSourceData(base=float(hp))
        container.stats["energy_max"] = StatSourceData(base=float(energy))
        container.stats["hp_regen"] = StatSourceData(base=0.0)

        await self.combat_manager.add_participant_id(session_id, char_id)
        await self.combat_manager.save_actor_json(session_id, char_id, container.model_dump_json())
        log.debug(f"CombatLifecycle | event=dummy_participant_added session_id='{session_id}' char_id={char_id}")

    async def initialize_battle_state(self, session_id: str) -> None:
        """
        Выполняет финальную настройку состояния боя перед его началом.

        Включает расчет целей для каждого участника и инициализацию зарядов тактики.

        Args:
            session_id: Идентификатор боевой сессии.
        """
        log.info(f"CombatLifecycle | event=initialize_battle_state session_id='{session_id}'")
        participants = await self.combat_manager.get_session_participants(session_id)
        actors_cache: dict[int, CombatSessionContainerDTO] = {}

        for pid_str in participants:
            pid = int(pid_str)
            try:
                data = await self.combat_manager.get_actor_json(session_id, pid)
                if data:
                    actors_cache[pid] = CombatSessionContainerDTO.model_validate_json(data)
            except (json.JSONDecodeError, ValueError):
                log.exception(
                    f"CombatLifecycle | status=failed reason='Actor data parse error' session_id='{session_id}' pid={pid}"
                )
                continue

        for pid, actor in actors_cache.items():
            if not actor.state:
                continue

            enemies = sorted(
                [
                    other_pid
                    for other_pid, other_actor in actors_cache.items()
                    if pid != other_pid and other_actor.team != actor.team
                ]
            )
            actor.state.targets = enemies

            enemy_count = len(enemies)
            charges = SWITCH_CHARGES_BASE + int(enemy_count * SWITCH_CHARGES_PER_ENEMY)
            cap = enemy_count * SWITCH_CHARGES_CAP_MULTIPLIER
            final_charges = min(charges, cap) if cap > 0 else charges
            actor.state.switch_charges = final_charges
            actor.state.max_switch_charges = cap

            await self.combat_manager.save_actor_json(session_id, pid, actor.model_dump_json())
            log.debug(
                f"CombatLifecycle | event=actor_state_initialized session_id='{session_id}' actor_id={pid} targets={enemies} charges={final_charges}"
            )

        log.info(
            f"CombatLifecycle | status=battle_state_initialized session_id='{session_id}' participants_count={len(participants)}"
        )

    async def finish_battle(self, session_id: str, winner_team: str) -> None:
        """
        Завершает боевую сессию, фиксирует результат, распределяет опыт и сохраняет
        актуальное состояние HP/Energy персонажей.

        Args:
            session_id: Идентификатор завершенной боевой сессии.
            winner_team: Команда-победитель (например, "blue", "red").
        """
        log.info(f"CombatLifecycle | event=finish_battle session_id='{session_id}' winner_team='{winner_team}'")
        end_time = int(time.time())
        meta = await self.combat_manager.get_session_meta(session_id)
        start_time = int(meta.get("start_time", end_time)) if meta else end_time
        duration = max(0, end_time - start_time)

        new_meta = {"active": 0, "winner": winner_team, "end_time": end_time}
        await self.combat_manager.create_session_meta(session_id, new_meta)

        participants_ids = await self.combat_manager.get_session_participants(session_id)
        stats_payload: dict[str, Any] = {
            "timestamp": end_time,
            "date_iso": date.today().isoformat(),
            "session_id": session_id,
            "winner_team": winner_team,
            "duration_sec": duration,
            "total_rounds": 0,
        }

        async with async_session_factory() as session:
            stats_repo, rate_repo, prog_repo = (
                get_character_stats_repo(session),
                get_skill_rate_repo(session),
                get_skill_progress_repo(session),
            )
            skill_service = CharacterSkillsService(stats_repo, rate_repo, prog_repo)

            p_counter = 1
            for pid_str in participants_ids:
                pid = int(pid_str)
                try:
                    data = await self.combat_manager.get_actor_json(session_id, pid)
                    if not data:
                        log.warning(
                            f"CombatLifecycle | reason='Actor data not found for XP/HP save' session_id='{session_id}' pid={pid}"
                        )
                        continue
                    actor = CombatSessionContainerDTO.model_validate_json(data)
                    if not actor.state:
                        log.warning(
                            f"CombatLifecycle | reason='Actor state not found for XP/HP save' session_id='{session_id}' pid={pid}"
                        )
                        continue

                    if actor.state.exchange_count > int(stats_payload["total_rounds"]):
                        stats_payload["total_rounds"] = actor.state.exchange_count

                    if p_counter <= 2:
                        prefix = f"p{p_counter}"
                        s = actor.state.stats
                        stats_payload.update(
                            {
                                f"{prefix}_id": actor.char_id,
                                f"{prefix}_name": actor.name,
                                f"{prefix}_team": actor.team,
                                f"{prefix}_hp_left": actor.state.hp_current,
                                f"{prefix}_energy_left": actor.state.energy_current,
                                f"{prefix}_dmg_dealt": s.damage_dealt,
                                f"{prefix}_dmg_taken": s.damage_taken,
                                f"{prefix}_healing": s.healing_done,
                                f"{prefix}_blocks": s.blocks_success,
                                f"{prefix}_dodges": s.dodges_success,
                                f"{prefix}_crits": s.crits_landed,
                            }
                        )
                        p_counter += 1

                    if not actor.is_ai and actor.state.xp_buffer:
                        log.info(
                            f"CombatLifecycle | event=saving_xp session_id='{session_id}' char_id={pid} xp_count={len(actor.state.xp_buffer)}"
                        )
                        await skill_service.apply_combat_xp_batch(pid, actor.state.xp_buffer)

                    if pid > 0:
                        await self.account_manager.update_account_fields(
                            pid,
                            {
                                "hp_current": actor.state.hp_current,
                                "energy_current": actor.state.energy_current,
                                "last_update": time.time(),
                            },
                        )
                        log.info(
                            f"CombatLifecycle | event=global_state_updated char_id={pid} hp={actor.state.hp_current} energy={actor.state.energy_current}"
                        )

                except (json.JSONDecodeError, ValueError):
                    log.exception(
                        f"CombatLifecycle | status=failed reason='Actor data processing error during finish' session_id='{session_id}' pid={pid}"
                    )
                    continue
            await session.commit()

        asyncio.create_task(analytics_service.log_combat_result(stats_payload))
        log.info(f"CombatLifecycle | event=analytics_task_created session_id='{session_id}'")
