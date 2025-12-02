# app/services/game_service/combat/combat_lifecycle_service.py
import asyncio
import json
import time
import uuid
from datetime import date
from typing import Any

from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from app.resources.schemas_dto.combat_source_dto import (
    CombatSessionContainerDTO,
    FighterStateDTO,
    StatSourceData,
)
from app.services.core_service.manager.account_manager import account_manager
from app.services.core_service.manager.combat_manager import combat_manager
from app.services.game_service.analytics.analytics_service import analytics_service
from app.services.game_service.combat.combat_aggregator import CombatAggregator
from app.services.game_service.combat.stats_calculator import StatsCalculator
from app.services.game_service.skill.skill_service import CharacterSkillsService
from database.repositories import (
    get_character_stats_repo,
    get_skill_progress_repo,
    get_skill_rate_repo,
)
from database.session import async_session_factory

# Константы
SWITCH_CHARGES_BASE = 1
SWITCH_CHARGES_PER_ENEMY = 0.5
SWITCH_CHARGES_CAP_MULTIPLIER = 5


class CombatLifecycleService:
    """
    Сервис управления Жизненным Циклом боя (Setup и Teardown).
    """

    @staticmethod
    async def create_battle(is_pve: bool = True, mode: str = "world") -> str:
        """
        Создает пустую сессию боя.
        mode: 'arena', 'dungeon', 'world' — определяет логику выхода.
        """
        session_id = str(uuid.uuid4())
        meta_data: dict[str, Any] = {
            "start_time": int(time.time()),
            "is_pve": int(is_pve),
            "active": 1,
            "mode": mode,
        }
        await combat_manager.create_session_meta(session_id, meta_data)
        log.info(f"BattleCreate | session_id={session_id} is_pve={is_pve} mode={mode}")
        return session_id

    @staticmethod
    async def add_participant(
        session: AsyncSession, session_id: str, char_id: int, team: str, name: str, is_ai: bool = False
    ) -> None:
        """
        Добавляет реального игрока или полноценного NPC в бой.
        FIX: Игнорируем прошлое состояние Redis и всегда даем Max HP/Energy.
        """
        log.info(f"AddParticipant | session_id={session_id} char_id={char_id} name='{name}' team={team} is_ai={is_ai}")
        aggregator = CombatAggregator(session)
        container = await aggregator.collect_session_container(char_id)
        container.team, container.name, container.is_ai = team, name, is_ai

        # FIX: Принудительный расчет Max HP/EN для СТАРТА
        final_stats = StatsCalculator.aggregate_all(container.stats)

        # Получаем Max HP/Energy по формулам.
        current_hp = int(final_stats.get("hp_max", 100))
        current_energy = int(final_stats.get("energy_max", 40))

        # Устанавливаем Max HP/Energy в новое состояние боя
        container.state = FighterStateDTO(
            hp_current=current_hp,  # <-- ВСЕГДА Max HP для старта
            energy_current=current_energy,  # <-- ВСЕГДА Max Energy для старта
            targets=[],
            switch_charges=0,
            max_switch_charges=0,
            xp_buffer={},
        )

        await combat_manager.add_participant_id(session_id, char_id)
        await combat_manager.save_actor_json(session_id, char_id, container.model_dump_json())
        log.debug(f"ParticipantAdded | session_id={session_id} char_id={char_id}")

    @staticmethod
    async def add_dummy_participant(session_id: str, char_id: int, hp: int, energy: int, name: str) -> None:
        """
        Добавляет манекен/тень с заданными параметрами.
        """
        log.info(f"AddDummyParticipant | session_id={session_id} char_id={char_id} name='{name}'")
        container = CombatSessionContainerDTO(char_id=char_id, team="red", name=name, is_ai=True)
        container.state = FighterStateDTO(
            hp_current=hp, energy_current=energy, targets=[], switch_charges=0, max_switch_charges=0, xp_buffer={}
        )
        container.stats["hp_max"] = StatSourceData(base=float(hp))
        container.stats["energy_max"] = StatSourceData(base=float(energy))
        container.stats["hp_regen"] = StatSourceData(base=0.0)

        await combat_manager.add_participant_id(session_id, char_id)
        await combat_manager.save_actor_json(session_id, char_id, container.model_dump_json())
        log.debug(f"DummyParticipantAdded | session_id={session_id} char_id={char_id}")

    @staticmethod
    async def initialize_battle_state(session_id: str) -> None:
        """
        Финальная настройка перед боем: расчет целей и зарядов тактики.
        """
        log.info(f"BattleStateInit | session_id={session_id}")
        participants = await combat_manager.get_session_participants(session_id)
        actors_cache: dict[int, CombatSessionContainerDTO] = {}

        for pid_str in participants:
            pid = int(pid_str)
            try:
                data = await combat_manager.get_actor_json(session_id, pid)
                if data:
                    actors_cache[pid] = CombatSessionContainerDTO.model_validate_json(data)
            except (json.JSONDecodeError, ValueError) as e:
                log.exception(
                    f"BattleStateInit_ActorParseFail | session_id={session_id} pid={pid} error='{e}'", exc_info=True
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

            await combat_manager.save_actor_json(session_id, pid, actor.model_dump_json())
            log.debug(
                f"ActorStateInitialized | session_id={session_id} actor_id={pid} targets={enemies} charges={final_charges}"
            )

        log.info(f"BattleStateInitSuccess | session_id={session_id} participants_count={len(participants)}")

    @staticmethod
    async def finish_battle(session_id: str, winner_team: str) -> None:
        """
        Завершает бой, фиксирует результат, раздает награды (XP).
        🔥 FIX: Сохраняет фактическое HP/EN в глобальный кэш (по запросу пользователя).
        """
        log.info(f"BattleFinish | session_id={session_id} winner_team={winner_team}")
        end_time = int(time.time())
        meta = await combat_manager.get_session_meta(session_id)
        start_time = int(meta.get("start_time", end_time)) if meta else end_time
        duration = max(0, end_time - start_time)

        new_meta = {"active": 0, "winner": winner_team, "end_time": end_time}
        await combat_manager.create_session_meta(session_id, new_meta)

        participants_ids = await combat_manager.get_session_participants(session_id)
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
                    data = await combat_manager.get_actor_json(session_id, pid)
                    if not data:
                        continue
                    actor = CombatSessionContainerDTO.model_validate_json(data)
                    if not actor.state:
                        continue

                    if actor.state.exchange_count > int(stats_payload["total_rounds"]):
                        stats_payload["total_rounds"] = actor.state.exchange_count

                    if p_counter <= 2:
                        prefix = f"p{p_counter}"
                        s = actor.state.stats

                        # Добавляем все поля для аналитики
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
                            f"SavingXP | session_id={session_id} char_id={pid} xp_count={len(actor.state.xp_buffer)}"
                        )
                        await skill_service.apply_combat_xp_batch(pid, actor.state.xp_buffer)

                    # 🔥 FIX: СОХРАНЯЕМ ТЕКУЩЕЕ HP/EN
                    # Сохраняем ТОЛЬКО то, что осталось после боя,
                    # чтобы реген начал работать от этой точки.
                    if pid > 0:  # Только для игроков
                        await account_manager.update_account_fields(
                            pid,
                            {
                                "hp_current": actor.state.hp_current,
                                "energy_current": actor.state.energy_current,
                                "last_update": time.time(),  # Обновляем для RegenService
                            },
                        )
                        log.info(f"GlobalStateUpdate | char_id={pid} HP saved as current ({actor.state.hp_current}).")

                except (json.JSONDecodeError, ValueError) as e:
                    log.exception(
                        f"FinishBattle_ActorParseFail | session_id={session_id} pid={pid} error='{e}'", exc_info=True
                    )
                    continue
            await session.commit()

        asyncio.create_task(analytics_service.log_combat_result(stats_payload))
        log.info(f"AnalyticsTaskCreated | session_id={session_id}")
