import asyncio
import json
import time
from datetime import date
from typing import Any

from loguru import logger as log
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
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
from apps.common.services.analytics.analytics_service import analytics_service
from apps.common.services.core_service import CombatManager
from apps.common.services.core_service.manager.account_manager import AccountManager
from apps.common.services.core_service.redis_fields import AccountFields as Af
from apps.game_core.game_service.combat.combat_redis_fields import CombatSessionFields as Csf
from apps.game_core.game_service.combat.core.combat_stats_calculator import StatsCalculator
from apps.game_core.game_service.combat.session.combat_aggregator import CombatAggregator
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
        """
        Инициализирует сервис.

        Args:
            combat_manager: Менеджер боя (Redis).
            account_manager: Менеджер аккаунта (Redis).
        """
        self.combat_manager = combat_manager
        self.account_manager = account_manager
        log.debug("CombatLifecycleServiceInit")

    async def create_battle(self, session_id: str, config: dict[str, Any]) -> None:
        """
        Создает новую боевую сессию в Redis с полными метаданными.

        Args:
            session_id: Уникальный ID сессии.
            config: Словарь с параметрами боя (battle_type, mode, is_pve и т.д.).
        """
        meta_data = {
            Csf.START_TIME: int(time.time()),
            Csf.ACTIVE: 1,
            Csf.TEAMS: json.dumps({}),  # Инициализируем пустые команды
            Csf.ACTORS_INFO: json.dumps({}),  # Инициализируем пустые роли
            Csf.DEAD_ACTORS: json.dumps([]),  # Инициализируем пустой список мертвых
            **config,  # Распаковываем весь конфиг сразу
        }
        # RBC: Пишем в новую мету
        await self.combat_manager.create_rbc_session_meta(session_id, meta_data)
        log.info(f"BattleCreate | session_id='{session_id}' config={config}")

    async def add_participant(
        self, session: AsyncSession, session_id: str, char_id: int, team: str, name: str, is_ai: bool = False
    ) -> None:
        """
        Добавляет участника в боевую сессию.

        Собирает все данные персонажа, рассчитывает HP/Energy и сохраняет в Redis.
        """
        log.info(f"AddParticipant | session_id='{session_id}' char_id={char_id} team='{team}' is_ai={is_ai}")
        try:
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

            # RBC: Пишем ТОЛЬКО в Hash акторов
            await self.combat_manager.set_rbc_actor_state_json(session_id, char_id, container.model_dump_json())

            # ВАЖНО: Привязываем сессию к аккаунту игрока (Mapping)
            if not is_ai:
                await self.account_manager.update_account_fields(char_id, {Af.COMBAT_SESSION_ID: session_id})

            log.debug(f"AddParticipant | event=success session_id='{session_id}' char_id={char_id}")
        except (SQLAlchemyError, ValidationError, json.JSONDecodeError) as e:
            log.exception(f"AddParticipantError | session_id='{session_id}' char_id={char_id} error='{e}'")

    async def add_dummy_participant(self, session_id: str, char_id: int, hp: int, energy: int, name: str) -> None:
        """
        Добавляет "манекен" в боевую сессию с заданными параметрами.
        """
        log.info(f"AddDummy | session_id='{session_id}' char_id={char_id} name='{name}'")
        container = CombatSessionContainerDTO(char_id=char_id, team="red", name=name, is_ai=True)
        container.state = FighterStateDTO(
            hp_current=hp, energy_current=energy, targets=[], switch_charges=0, max_switch_charges=0, xp_buffer={}
        )
        container.stats["hp_max"] = StatSourceData(base=float(hp))
        container.stats["energy_max"] = StatSourceData(base=float(energy))
        container.stats["hp_regen"] = StatSourceData(base=0.0)

        # RBC: Пишем ТОЛЬКО в Hash акторов
        await self.combat_manager.set_rbc_actor_state_json(session_id, char_id, container.model_dump_json())
        log.debug(f"AddDummy | event=success session_id='{session_id}' char_id={char_id}")

    async def create_shadow_copy(self, session_id: str, original_char_id: int) -> None:
        """
        Создает теневую копию участника (клон) для режима arena_shadow.
        """
        player_json = await self.combat_manager.get_rbc_actor_state_json(session_id, original_char_id)

        if not player_json:
            log.warning(
                f"CreateShadowCopy | reason=original_not_found session_id='{session_id}' original_id={original_char_id}"
            )
            return

        try:
            player_data = CombatSessionContainerDTO.model_validate_json(player_json)
            shadow_id = -original_char_id

            # Клонируем данные
            shadow_data = player_data.model_copy(deep=True)
            shadow_data.char_id = shadow_id
            shadow_data.name = f"👥 Тень ({player_data.name})"
            shadow_data.team = "red"
            shadow_data.is_ai = True

            # RBC: Пишем ТОЛЬКО в Hash акторов
            await self.combat_manager.set_rbc_actor_state_json(session_id, shadow_id, shadow_data.model_dump_json())
            log.info(f"CreateShadowCopy | event=success session_id='{session_id}' shadow_id={shadow_id}")
        except (ValidationError, json.JSONDecodeError) as e:
            log.exception(f"CreateShadowCopyError | session_id='{session_id}' error='{e}'")

    async def initialize_exchange_queues(self, session_id: str, players: list[int]) -> None:
        """
        Наполняет очереди обменов для игроков.
        """
        actors_data = await self.combat_manager.get_rbc_all_actors_json(session_id)
        actors_teams = {}
        if actors_data:
            for aid, data in actors_data.items():
                container = CombatSessionContainerDTO.model_validate_json(data)
                actors_teams[int(aid)] = container.team

        for p_id in players:
            player_team = actors_teams.get(p_id)
            enemies_ids = [str(aid) for aid, team in actors_teams.items() if team != player_team]

            if enemies_ids:
                # ИСПРАВЛЕНО: Используем метод менеджера вместо прямого доступа к Redis
                await self.combat_manager.add_enemies_to_exchange_queue(session_id, p_id, enemies_ids)
        log.debug(f"InitializeExchangeQueues | session_id='{session_id}' players={players}")

    async def initialize_battle_state(self, session_id: str) -> None:
        """
        Выполняет финальную настройку состояния боя перед его началом.

        Рассчитывает цели для каждого участника и инициализирует заряды тактики.
        Также обновляет метаданные сессии (teams, actors_info).
        """
        log.info(f"InitializeBattle | session_id='{session_id}'")
        # Теперь читаем всех актеров сразу из RBC хэша
        actors_data = await self.combat_manager.get_rbc_all_actors_json(session_id)

        if not actors_data:
            log.warning(f"InitializeBattle | status=empty session_id='{session_id}'")
            return

        actors_cache: dict[int, CombatSessionContainerDTO] = {}
        teams_map: dict[str, list[int]] = {}
        actors_info: dict[str, str] = {}

        for aid_str, data in actors_data.items():
            pid = int(aid_str)
            try:
                actor = CombatSessionContainerDTO.model_validate_json(data)
                actors_cache[pid] = actor

                # Заполняем teams и actors_info
                if actor.team not in teams_map:
                    teams_map[actor.team] = []
                teams_map[actor.team].append(pid)

                actors_info[str(pid)] = "ai" if actor.is_ai else "player"

            except (json.JSONDecodeError, ValidationError) as e:
                log.exception(
                    f"InitializeBattleError | reason=actor_parse_fail session_id='{session_id}' pid={pid} error='{e}'"
                )
                continue

        # Обновляем метаданные сессии
        meta_update = {Csf.TEAMS: json.dumps(teams_map), Csf.ACTORS_INFO: json.dumps(actors_info)}
        await self.combat_manager.create_rbc_session_meta(session_id, meta_update)

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

            # Сохраняем обратно в RBC ключ
            await self.combat_manager.set_rbc_actor_state_json(session_id, pid, actor.model_dump_json())
            log.debug(
                f"InitializeBattle | event=actor_state_init session_id='{session_id}' actor_id={pid} targets={enemies} charges={final_charges}"
            )
        log.info(f"InitializeBattle | event=success session_id='{session_id}' participants={len(actors_cache)}")

    async def finish_battle(self, session_id: str, winner_team: str) -> None:
        """
        Завершает боевую сессию, распределяет опыт и сохраняет состояние персонажей.
        """
        log.info(f"FinishBattle | session_id='{session_id}' winner_team='{winner_team}'")
        end_time = int(time.time())
        # RBC: Читаем из новой меты
        meta = await self.combat_manager.get_rbc_session_meta(session_id)
        start_time = int(meta.get(Csf.START_TIME, end_time)) if meta else end_time
        duration = max(0, end_time - start_time)

        # Читаем участников из RBC хэша
        actors_data = await self.combat_manager.get_rbc_all_actors_json(session_id)
        if not actors_data:
            log.warning(f"FinishBattle | reason=no_actors_found session_id='{session_id}'")
            return

        # Собираем награды (rewards) для каждого игрока
        # В будущем здесь может быть логика лута, пока только опыт
        rewards_map = {}

        stats_payload: dict[str, Any] = {
            "timestamp": end_time,
            "date_iso": date.today().isoformat(),
            "session_id": session_id,
            "winner_team": winner_team,
            "duration_sec": duration,
            "total_rounds": 0,
        }

        try:
            async with async_session_factory() as session:
                stats_repo, rate_repo, prog_repo = (
                    get_character_stats_repo(session),
                    get_skill_rate_repo(session),
                    get_skill_progress_repo(session),
                )
                skill_service = CharacterSkillsService(stats_repo, rate_repo, prog_repo)

                p_counter = 1
                for pid_str, data in actors_data.items():
                    pid = int(pid_str)
                    try:
                        actor = CombatSessionContainerDTO.model_validate_json(data)
                        if not actor.state:
                            log.warning(
                                f"FinishBattle | reason=actor_state_missing session_id='{session_id}' pid={pid}"
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

                        # Обработка опыта
                        xp_gained = 0
                        if not actor.is_ai and actor.state.xp_buffer:
                            log.info(
                                f"FinishBattle | event=saving_xp char_id={pid} xp_count={len(actor.state.xp_buffer)}"
                            )
                            # Суммируем опыт для отображения в UI
                            xp_gained = sum(actor.state.xp_buffer.values())
                            await skill_service.apply_combat_xp_batch(pid, actor.state.xp_buffer)

                        # Формируем структуру наград для UI
                        rewards_map[str(pid)] = {
                            "xp": xp_gained,
                            "gold": 0,  # Пока заглушка
                            "items": [],
                        }

                        if pid > 0:
                            # ВАЖНО: Очищаем combat_session_id у игрока
                            # Используем пустую строку вместо None, чтобы Redis не ругался
                            await self.account_manager.update_account_fields(
                                pid,
                                {
                                    Af.HP_CURRENT: actor.state.hp_current,
                                    Af.ENERGY_CURRENT: actor.state.energy_current,
                                    Af.LAST_UPDATE: time.time(),
                                    Af.COMBAT_SESSION_ID: "",  # <--- ИСПРАВЛЕНО: Пустая строка вместо None
                                },
                            )
                            log.info(
                                f"FinishBattle | event=global_state_update char_id={pid} hp={actor.state.hp_current}"
                            )

                    except (json.JSONDecodeError, ValidationError) as e:
                        log.exception(
                            f"FinishBattleError | reason=actor_parse_fail session_id='{session_id}' pid={pid} error='{e}'"
                        )
                        continue
                await session.commit()
        except SQLAlchemyError as e:
            log.exception(f"FinishBattleError | reason=db_error session_id='{session_id}' error='{e}'")

        # Сохраняем rewards в метаданные сессии, чтобы UI мог их прочитать
        new_meta = {
            Csf.ACTIVE: 0,
            Csf.WINNER: winner_team,
            Csf.END_TIME: end_time,
            Csf.REWARDS: json.dumps(rewards_map),  # <--- Добавили сохранение наград
        }
        # RBC: Обновляем новую мету
        await self.combat_manager.create_rbc_session_meta(session_id, new_meta)

        # RBC: Очистка сессии (удаление очередей, пуль и установка TTL на историю)
        await self.combat_manager.cleanup_rbc_session(session_id)

        asyncio.create_task(analytics_service.log_combat_result(stats_payload))
        log.info(f"FinishBattle | event=analytics_task_created session_id='{session_id}'")
