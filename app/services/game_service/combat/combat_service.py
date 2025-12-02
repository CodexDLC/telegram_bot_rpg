# app/services/game_service/combat/combat_service.py
import json
import random
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

# Импортируем наш новый менеджер опыта (он просто хелпер, не сервис)
from app.services.core_service.manager.combat_manager import combat_manager
from app.services.game_service.analytics.analytics_service import analytics_service
from app.services.game_service.combat.ability_service import AbilityService
from app.services.game_service.combat.combat_aggregator import CombatAggregator
from app.services.game_service.combat.combat_ai_service import CombatAIService
from app.services.game_service.combat.combat_calculator import CombatCalculator
from app.services.game_service.combat.combat_log_builder import CombatLogBuilder
from app.services.game_service.combat.combat_xp_manager import CombatXPManager
from app.services.game_service.combat.stats_calculator import StatsCalculator
from app.services.game_service.regen_service import RegenService
from app.services.game_service.skill.skill_service import CharacterSkillsService

# Импорты репозиториев нужны для создания сессии в _finish_battle
from database.repositories import get_character_stats_repo, get_skill_progress_repo, get_skill_rate_repo

VALID_BLOCK_PAIRS = [
    ["head", "chest"],
    ["chest", "legs"],
    ["legs", "feet"],
    ["feet", "head"],
]

SWITCH_CHARGES_BASE = 1
SWITCH_CHARGES_PER_ENEMY = 0.5
SWITCH_CHARGES_CAP_MULTIPLIER = 5
TURN_TIMEOUT = 60


class CombatService:
    """
    Сервис-оркестратор боя.
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        log.debug(f"CombatService инициализирован для сессии {session_id}")

    # =========================================================================
    # 1. ИНИЦИАЛИЗАЦИЯ БОЯ
    # =========================================================================

    @staticmethod
    async def create_battle(participants: list[dict], is_pve: bool = True) -> str:
        session_id = str(uuid.uuid4())
        meta_data: dict[str, Any] = {
            "start_time": int(time.time()),
            "is_pve": int(is_pve),
            "active": 1,
        }
        await combat_manager.create_session_meta(session_id, meta_data)
        log.info(f"Бой {session_id} (PvE: {is_pve}) создан. Участников: {len(participants)}")
        return session_id

    async def add_participant(
        self,
        session: AsyncSession,
        char_id: int,
        team: str,
        name: str,
        is_ai: bool = False,
    ) -> None:
        log.debug(f"Добавление участника {char_id} ({name}) в команду {team}...")
        aggregator = CombatAggregator(session)
        container = await aggregator.collect_session_container(char_id)
        container.team = team
        container.name = name
        container.is_ai = is_ai

        regen_service = RegenService(session)
        current_state = await regen_service.synchronize_state(char_id)

        if current_state["hp"] == 0 and not is_ai:
            final_stats = StatsCalculator.aggregate_all(container.stats)
            current_hp = int(final_stats.get("hp_max", 1))
            current_energy = int(final_stats.get("energy_max", 0))
            log.warning(f"HP бойца {char_id} было 0, восстановлено до {current_hp}")
        else:
            current_hp = current_state["hp"]
            current_energy = current_state["energy"]

        # Инициализируем xp_buffer
        container.state = FighterStateDTO(
            hp_current=current_hp,
            energy_current=current_energy,
            targets=[],
            switch_charges=0,
            max_switch_charges=0,
            xp_buffer={},  # <--- ВАЖНО: Пустой буфер
        )

        await combat_manager.add_participant_id(self.session_id, char_id)
        await combat_manager.save_actor_json(self.session_id, char_id, container.model_dump_json())
        log.info(f"Участник {name} ({char_id}) успешно добавлен в бой {self.session_id}.")

    async def add_dummy_participant(self, char_id: int, hp: int, energy: int, name: str) -> None:
        log.debug(f"Добавление Тени {name} ({char_id}) с {hp} HP / {energy} EN.")
        container = CombatSessionContainerDTO(char_id=char_id, team="red", name=name, is_ai=True)

        container.state = FighterStateDTO(
            hp_current=hp, energy_current=energy, targets=[], switch_charges=0, max_switch_charges=0, xp_buffer={}
        )

        container.stats["hp_max"] = StatSourceData(base=float(hp))
        container.stats["energy_max"] = StatSourceData(base=float(energy))
        container.stats["hp_regen"] = StatSourceData(base=0.0)

        await combat_manager.add_participant_id(self.session_id, char_id)
        await combat_manager.save_actor_json(self.session_id, char_id, container.model_dump_json())

    # =========================================================================
    # МЕТОДЫ УПРАВЛЕНИЯ (Без изменений)
    # =========================================================================

    async def initialize_battle_state(self) -> None:
        participants = await combat_manager.get_session_participants(self.session_id)

        for pid_str in participants:
            pid = int(pid_str)
            actor = await self._get_actor(pid)
            if not actor or not actor.state:
                continue

            enemies = []
            for other_pid_str in participants:
                other_pid = int(other_pid_str)
                if other_pid == pid:
                    continue

                other = await self._get_actor(other_pid)
                if other and other.team != actor.team:
                    enemies.append(other_pid)

            enemies.sort()
            actor.state.targets = enemies

            enemy_count = len(enemies)
            charges = SWITCH_CHARGES_BASE + int(enemy_count * SWITCH_CHARGES_PER_ENEMY)
            cap = enemy_count * SWITCH_CHARGES_CAP_MULTIPLIER
            final_charges = min(charges, cap) if cap > 0 else charges

            actor.state.switch_charges = final_charges
            actor.state.max_switch_charges = cap

            await combat_manager.save_actor_json(self.session_id, pid, actor.model_dump_json())
            log.info(f"Боец {pid}: Врагов={enemy_count}, Зарядов={final_charges}, Очередь={enemies}")

    async def switch_target(self, actor_id: int, new_target_id: int) -> tuple[bool, str]:
        actor = await self._get_actor(actor_id)
        if not actor or not actor.state:
            return False, "Ошибка данных бойца."

        if not actor.state.targets:
            return False, "Нет доступных целей."

        if new_target_id not in actor.state.targets:
            return False, "Недопустимая цель."

        if actor.state.targets[0] == new_target_id:
            return False, "Эта цель уже выбрана."

        if actor.state.switch_charges <= 0:
            return False, "Не хватает тактических очков смены."

        actor.state.switch_charges -= 1

        try:
            new_target_index = actor.state.targets.index(new_target_id)
            actor.state.targets[0], actor.state.targets[new_target_index] = (
                actor.state.targets[new_target_index],
                actor.state.targets[0],
            )
        except ValueError:
            return False, "Ошибка ротации списка."

        await combat_manager.save_actor_json(self.session_id, actor_id, actor.model_dump_json())
        return True, f"Цель изменена. Осталось смен: {actor.state.switch_charges}"

    # =========================================================================
    # РЕГИСТРАЦИЯ ХОДА (Без изменений)
    # =========================================================================

    async def register_move(
        self,
        actor_id: int,
        target_id: int | None,
        attack_zones: list[str] | None,
        block_zones: list[str] | None,
        ability_key: str | None = None,
    ) -> None:
        actor = await self._get_actor(actor_id)
        if not actor or not actor.state:
            log.error(f"register_move: Боец {actor_id} не найден.")
            return

        real_target_id = target_id
        if real_target_id is None:
            if actor.state.targets:
                real_target_id = actor.state.targets[0]
            else:
                log.warning(f"Боец {actor_id} пытается сделать ход, но нет целей.")
                return

        if not attack_zones:
            attack_zones = [random.choice(["head", "chest", "legs", "feet"])]
        if not block_zones:
            block_zones = random.choice(VALID_BLOCK_PAIRS)

        deadline = int(time.time() + TURN_TIMEOUT)

        move_data = {
            "target_id": real_target_id,
            "attack": attack_zones,
            "block": block_zones,
            "ability": ability_key,
            "timestamp": time.time(),
            "deadline": deadline,
        }
        move_json = json.dumps(move_data)

        await combat_manager.set_pending_move(self.session_id, actor_id, real_target_id, move_json)
        log.debug(f"Заявка {actor_id} -> {real_target_id} (Deadline: {deadline})")

        counter_move_json = await combat_manager.get_pending_move(self.session_id, real_target_id, actor_id)

        if counter_move_json:
            counter_move = json.loads(counter_move_json)

            await combat_manager.delete_pending_move(self.session_id, actor_id, real_target_id)
            await combat_manager.delete_pending_move(self.session_id, real_target_id, actor_id)

            await self._process_exchange(actor_id, move_data, real_target_id, counter_move)
            await self._process_ai_turns()
            await self.check_deadlines()

        else:
            target_actor = await self._get_actor(real_target_id)
            if target_actor and target_actor.is_ai:
                decision = await CombatAIService.calculate_action(target_actor, self.session_id)
                if decision:
                    await self._process_ai_turns()

    async def check_deadlines(self) -> None:
        participants = await combat_manager.get_session_participants(self.session_id)
        now = time.time()

        for pid_str in participants:
            actor_id = int(pid_str)
            actor = await self._get_actor(actor_id)
            if not actor or not actor.state or not actor.state.targets:
                continue

            target_id = actor.state.targets[0]
            pending_json = await combat_manager.get_pending_move(self.session_id, actor_id, target_id)
            if pending_json:
                data = json.loads(pending_json)
                deadline = data.get("deadline", 0)

                if 0 < deadline < now:
                    log.warning(f"⏰ Таймер истек для пары {actor_id}->{target_id}. Принудительный ход {target_id}.")
                    await self.register_move(
                        actor_id=target_id,
                        target_id=actor_id,
                        attack_zones=None,
                        block_zones=None,
                        ability_key=None,
                    )

    async def _process_ai_turns(self) -> None:
        participants = await combat_manager.get_session_participants(self.session_id)
        for pid_str in participants:
            pid = int(pid_str)
            actor = await self._get_actor(pid)

            if not actor or not actor.is_ai or (actor.state and actor.state.hp_current <= 0):
                continue

            decision = await CombatAIService.calculate_action(actor, self.session_id)
            if not decision:
                continue

            target_id = decision.get("target_id")
            if not target_id:
                continue

            existing = await combat_manager.get_pending_move(self.session_id, pid, target_id)
            if existing:
                continue

            await self.register_move(
                actor_id=pid,
                target_id=target_id,
                attack_zones=decision["attack"],
                block_zones=decision["block"],
                ability_key=decision.get("ability"),
            )

    # =========================================================================
    # СТАТИСТИКА И КОНТРОЛЬ БОЯ
    # =========================================================================

    def _update_stats(self, actor: CombatSessionContainerDTO, result_outgoing: dict, result_incoming: dict) -> None:
        if not actor.state:
            return

        stats = actor.state.stats
        stats.damage_dealt += result_outgoing.get("damage_total", 0)
        if result_outgoing.get("is_crit"):
            stats.crits_landed += 1
        stats.healing_done += result_outgoing.get("lifesteal", 0)
        stats.damage_taken += result_incoming.get("damage_total", 0)
        if result_incoming.get("is_blocked"):
            stats.blocks_success += 1
        if result_incoming.get("is_dodged"):
            stats.dodges_success += 1

    async def _check_death_event(self, actor: CombatSessionContainerDTO) -> None:
        if actor.state and actor.state.hp_current <= 0:
            log.info(f"💀 Боец {actor.name} ({actor.char_id}) погиб.")

    async def _check_battle_end(self) -> bool:
        participants = await combat_manager.get_session_participants(self.session_id)
        teams_alive = set()

        for pid_str in participants:
            pid = int(pid_str)
            actor = await self._get_actor(pid)
            if not actor or not actor.state:
                continue

            if actor.state.hp_current > 0:
                teams_alive.add(actor.team)

        if len(teams_alive) <= 1:
            winner_team = list(teams_alive)[0] if teams_alive else "none"
            await self._finish_battle(winner_team)
            return True

        return False

    async def _finish_battle(self, winner_team: str) -> None:
        log.info(f"🏆 БОЙ {self.session_id} ЗАВЕРШЕН. Победитель: {winner_team}")

        end_time = int(time.time())
        meta = await combat_manager.get_session_meta(self.session_id)
        start_time = int(meta.get("start_time", end_time)) if meta else end_time
        duration = max(0, end_time - start_time)

        new_meta = {"active": 0, "winner": winner_team, "end_time": end_time}
        await combat_manager.create_session_meta(self.session_id, new_meta)

        participants_ids = await combat_manager.get_session_participants(self.session_id)

        # --------------------------------------------------------
        # 🔥 ИНТЕГРАЦИЯ: Сброс Опыта из Буфера в БД
        # --------------------------------------------------------
        from database.session import async_session_factory

        async with async_session_factory() as session:
            # Создаем сервисы внутри сессии
            stats_repo = get_character_stats_repo(session)
            rate_repo = get_skill_rate_repo(session)
            prog_repo = get_skill_progress_repo(session)

            # Наш skill_service с новым методом
            skill_service = CharacterSkillsService(stats_repo, rate_repo, prog_repo)

            stats_payload: dict[str, Any] = {
                "timestamp": end_time,
                "date_iso": date.today().isoformat(),
                "session_id": self.session_id,
                "winner_team": winner_team,
                "duration_sec": duration,
                "total_rounds": 0,
            }

            p_counter = 1

            for pid_str in participants_ids:
                pid = int(pid_str)
                actor = await self._get_actor(pid)

                if not actor or not actor.state:
                    continue

                # Аналитика
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
                            f"{prefix}_dmg_dealt": s.damage_dealt,
                        }
                    )
                    p_counter += 1

                # ✅ ВЫЗОВ: Сброс опыта из Redis в БД
                # Только для живых игроков (у AI нет записей в БД навыков)
                if not actor.is_ai and actor.state.xp_buffer:
                    log.info(f"Сохранение опыта для {actor.name}...")
                    await skill_service.apply_combat_xp_batch(pid, actor.state.xp_buffer)

            # Фиксируем изменения в БД
            await session.commit()

        # Аналитика (Fire and Forget)
        import asyncio

        asyncio.create_task(analytics_service.log_combat_result(stats_payload))

    # =========================================================================
    # 3. ЯДРО: РАСЧЕТ ОБМЕНА УДАРАМИ (С ИНТЕГРАЦИЕЙ XP MANAGER)
    # =========================================================================

    async def _process_exchange(self, id_a: int, move_a: dict, id_b: int, move_b: dict) -> None:
        log.debug(f"Начало обмена ударами между {id_a} и {id_b}.")
        actor_a = await self._get_actor(id_a)
        actor_b = await self._get_actor(id_b)

        if not actor_a or not actor_b or not actor_a.state or not actor_b.state:
            log.error("Критическая ошибка: данные бойцов не загружены.")
            return

        stats_a = StatsCalculator.aggregate_all(actor_a.stats)
        stats_b = StatsCalculator.aggregate_all(actor_b.stats)

        skill_key_a = move_a.get("ability")
        skill_key_b = move_b.get("ability")

        pipeline_a = AbilityService.get_full_pipeline(actor_a, skill_key_a)
        pipeline_b = AbilityService.get_full_pipeline(actor_b, skill_key_b)

        flags_a = dict(AbilityService.get_ability_rules(skill_key_a)) if skill_key_a else {}
        flags_b = dict(AbilityService.get_ability_rules(skill_key_b)) if skill_key_b else {}

        AbilityService.execute_pre_calc(stats_a, flags_a, pipeline_a)
        AbilityService.execute_pre_calc(stats_b, flags_b, pipeline_b)

        # CALCULATION
        res_a_to_b = CombatCalculator.calculate_hit(
            stats_atk=stats_a,
            stats_def=stats_b,
            current_shield=actor_b.state.energy_current,
            attack_zones=move_a["attack"],
            block_zones=move_b["block"],
            flags=flags_a,
        )

        res_b_to_a = CombatCalculator.calculate_hit(
            stats_atk=stats_b,
            stats_def=stats_a,
            current_shield=actor_a.state.energy_current,
            attack_zones=move_b["attack"],
            block_zones=move_a["block"],
            flags=flags_b,
        )

        AbilityService.execute_post_calc(res_a_to_b, actor_a, actor_b, pipeline_a)
        AbilityService.execute_post_calc(res_b_to_a, actor_b, actor_a, pipeline_b)

        if skill_key_a:
            AbilityService.consume_resources(actor_a, skill_key_a)
        if skill_key_b:
            AbilityService.consume_resources(actor_b, skill_key_b)

        # --------------------------------------------------------
        # 🔥 ИНТЕГРАЦИЯ: Начисление опыта в БУФЕР (через Manager)
        # --------------------------------------------------------

        # 1. АТАКУЮЩИЙ ОПЫТ (Оружие)
        outcome_a = "success"
        if res_a_to_b["is_dodged"]:
            outcome_a = "miss"
        elif res_a_to_b["is_blocked"]:
            outcome_a = "partial"
        elif res_a_to_b["is_crit"]:
            outcome_a = "crit"

        # Делегируем логику Менеджеру (он сам добавит в xp_buffer)
        CombatXPManager.register_action(actor_a, "sword", outcome_a)

        outcome_b = "success"
        if res_b_to_a["is_dodged"]:
            outcome_b = "miss"
        elif res_b_to_a["is_blocked"]:
            outcome_b = "partial"
        elif res_b_to_a["is_crit"]:
            outcome_b = "crit"

        CombatXPManager.register_action(actor_b, "sword", outcome_b)

        # 2. ПАССИВНЫЙ ОПЫТ (Броня) - если получен урон
        if res_b_to_a["damage_total"] > 0:
            CombatXPManager.register_action(actor_a, "medium", "success")
        if res_a_to_b["damage_total"] > 0:
            CombatXPManager.register_action(actor_b, "medium", "success")

        # 3. ЩИТ - если блок сработал
        if res_b_to_a["is_blocked"]:
            CombatXPManager.register_action(actor_a, "shield", "success")
        if res_a_to_b["is_blocked"]:
            CombatXPManager.register_action(actor_b, "shield", "success")

        # --- Применение результатов ---
        self._apply_hit_result(actor_b, res_a_to_b)
        self._apply_hit_result(actor_a, res_b_to_a)

        self._apply_tokens(actor_a, res_a_to_b.get("tokens_atk", {}), res_b_to_a.get("tokens_def", {}))
        self._apply_tokens(actor_b, res_b_to_a.get("tokens_atk", {}), res_a_to_b.get("tokens_def", {}))

        self._apply_regen(actor_a, stats_a)
        self._apply_regen(actor_b, stats_b)

        actor_a.state.exchange_count += 1
        actor_b.state.exchange_count += 1

        self._update_stats(actor_a, res_a_to_b, res_b_to_a)
        self._update_stats(actor_b, res_b_to_a, res_a_to_b)

        await combat_manager.save_actor_json(self.session_id, id_a, actor_a.model_dump_json())
        await combat_manager.save_actor_json(self.session_id, id_b, actor_b.model_dump_json())

        await self._log_exchange(actor_a, res_a_to_b, actor_b, res_b_to_a)

        await self._check_death_event(actor_a)
        await self._check_death_event(actor_b)

        if await self._check_battle_end():
            return

        log.info(f"Обмен {id_a} vs {id_b} завершен (XP начислен в буфер).")

    # =========================================================================
    # 4. ХЕЛПЕРЫ (Без изменений)
    # =========================================================================

    def _apply_hit_result(self, actor: CombatSessionContainerDTO, result: dict) -> None:
        if not actor.state:
            return
        actor.state.energy_current = max(0, actor.state.energy_current - result["shield_dmg"])
        actor.state.hp_current = max(0, actor.state.hp_current - result["hp_dmg"])
        if result["hp_dmg"] > 0 and actor.state.hp_current <= 0:
            result["logs"].append("💀 <b>Удар добил противника!</b>")

    def _apply_tokens(self, actor: CombatSessionContainerDTO, atk_tokens: dict, def_tokens: dict) -> None:
        if not actor.state:
            return
        if not actor.state.tokens:
            actor.state.tokens = {}
        for token_type, count in atk_tokens.items():
            actor.state.tokens[token_type] = actor.state.tokens.get(token_type, 0) + count
        for token_type, count in def_tokens.items():
            actor.state.tokens[token_type] = actor.state.tokens.get(token_type, 0) + count

    async def _log_exchange(
        self,
        actor_a: CombatSessionContainerDTO,
        res_a: dict,
        actor_b: CombatSessionContainerDTO,
        res_b: dict,
    ) -> None:
        combined_logs = []
        text_a = CombatLogBuilder.build_log_entry(actor_a.name, actor_b.name, res_a)
        combined_logs.append(text_a)
        text_b = CombatLogBuilder.build_log_entry(actor_b.name, actor_a.name, res_b)
        combined_logs.append(text_b)

        log_entry: dict[str, Any] = {
            "time": time.time(),
            "round_index": actor_a.state.exchange_count if actor_a.state else 0,
            "pair_names": [actor_a.name, actor_b.name],
            "logs": combined_logs,
        }
        await combat_manager.push_combat_log(self.session_id, json.dumps(log_entry))

    def _apply_regen(self, actor: CombatSessionContainerDTO, stats: dict[str, float]) -> None:
        if not actor.state or actor.state.hp_current <= 0:
            return
        regen_hp = int(stats.get("hp_regen", 0))
        max_hp = int(stats.get("hp_max", 1))
        if regen_hp > 0 and actor.state.hp_current < max_hp:
            actor.state.hp_current = min(max_hp, actor.state.hp_current + regen_hp)
        regen_en = int(stats.get("energy_regen", 0))
        max_en = int(stats.get("energy_max", 0))
        if regen_en > 0 and actor.state.energy_current < max_en:
            actor.state.energy_current = min(max_en, actor.state.energy_current + regen_en)

    async def _get_actor(self, char_id: int) -> CombatSessionContainerDTO | None:
        data = await combat_manager.get_actor_json(self.session_id, char_id)
        if data:
            try:
                return CombatSessionContainerDTO.model_validate_json(data)
            except json.JSONDecodeError as e:
                log.exception(f"Ошибка десериализации данных для char_id={char_id}: {e}")
                return None
        log.warning(f"Не найдены данные для бойца {char_id} в сессии {self.session_id}.")
        return None
