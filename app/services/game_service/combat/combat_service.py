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
from app.services.core_service.manager.combat_manager import combat_manager
from app.services.game_service.analytics.analytics_service import analytics_service
from app.services.game_service.combat.ability_service import AbilityService
from app.services.game_service.combat.combat_aggregator import CombatAggregator
from app.services.game_service.combat.combat_ai_service import CombatAIService
from app.services.game_service.combat.combat_calculator import CombatCalculator
from app.services.game_service.combat.combat_log_builder import CombatLogBuilder
from app.services.game_service.combat.stats_calculator import StatsCalculator
from app.services.game_service.regen_service import RegenService

VALID_BLOCK_PAIRS = [
    ["head", "chest"],
    ["chest", "legs"],
    ["legs", "feet"],
    ["feet", "head"],
]

# =========================================================================
# ⚙️ НАСТРОЙКИ МЕХАНИКИ "СМЕНА ЦЕЛИ"
# =========================================================================
SWITCH_CHARGES_BASE = 1  # Базовое количество смен
SWITCH_CHARGES_PER_ENEMY = 0.5  # Зарядов за каждого врага (0.5 = 1 заряд за 2 врагов)
SWITCH_CHARGES_CAP_MULTIPLIER = 5  # Кап = Кол-во врагов * этот множитель
TURN_TIMEOUT = 60  # Время на ход в секундах


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

        container.state = FighterStateDTO(
            hp_current=current_hp,
            energy_current=current_energy,
            targets=[],
            switch_charges=0,
            max_switch_charges=0,
        )

        await combat_manager.add_participant_id(self.session_id, char_id)
        await combat_manager.save_actor_json(self.session_id, char_id, container.model_dump_json())
        log.info(f"Участник {name} ({char_id}) успешно добавлен в бой {self.session_id}.")

    async def add_dummy_participant(self, char_id: int, hp: int, energy: int, name: str) -> None:
        log.debug(f"Добавление Тени {name} ({char_id}) с {hp} HP / {energy} EN.")
        container = CombatSessionContainerDTO(char_id=char_id, team="red", name=name, is_ai=True)

        container.state = FighterStateDTO(
            hp_current=hp,
            energy_current=energy,
            targets=[],
            switch_charges=0,
            max_switch_charges=0,
        )

        container.stats["hp_max"] = StatSourceData(base=float(hp))
        container.stats["energy_max"] = StatSourceData(base=float(energy))
        container.stats["hp_regen"] = StatSourceData(base=0.0)

        await combat_manager.add_participant_id(self.session_id, char_id)
        await combat_manager.save_actor_json(self.session_id, char_id, container.model_dump_json())

    # =========================================================================
    # 🆕 МЕТОДЫ УПРАВЛЕНИЯ ЦЕЛЯМИ И ЗАРЯДАМИ
    # =========================================================================

    async def initialize_battle_state(self) -> None:
        """
        Вызывается ПОСЛЕ добавления всех участников.
        Рассчитывает очереди целей и заряды.
        """
        participants = await combat_manager.get_session_participants(self.session_id)

        for pid_str in participants:
            pid = int(pid_str)
            actor = await self._get_actor(pid)
            if not actor or not actor.state:
                continue

            # 1. Формируем список врагов
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

            # 2. Расчет зарядов
            enemy_count = len(enemies)
            charges = SWITCH_CHARGES_BASE + int(enemy_count * SWITCH_CHARGES_PER_ENEMY)
            cap = enemy_count * SWITCH_CHARGES_CAP_MULTIPLIER
            final_charges = min(charges, cap) if cap > 0 else charges

            actor.state.switch_charges = final_charges
            actor.state.max_switch_charges = cap

            await combat_manager.save_actor_json(self.session_id, pid, actor.model_dump_json())
            log.info(f"Боец {pid}: Врагов={enemy_count}, Зарядов={final_charges}, Очередь={enemies}")

    async def switch_target(self, actor_id: int, new_target_id: int) -> tuple[bool, str]:
        """
        Тактическое действие: Смена цели.
        """
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

        # 1. Списываем заряд
        actor.state.switch_charges -= 1

        # 2. Ротация очереди (SWAP)
        try:
            # Находим, где сейчас новая цель
            new_target_index = actor.state.targets.index(new_target_id)

            # Меняем местами: Текущая (0) <-> Новая (index)
            # Старая цель улетает в глубину списка на место новой
            actor.state.targets[0], actor.state.targets[new_target_index] = (
                actor.state.targets[new_target_index],
                actor.state.targets[0],
            )
        except ValueError:
            return False, "Ошибка ротации списка."

        await combat_manager.save_actor_json(self.session_id, actor_id, actor.model_dump_json())
        return True, f"Цель изменена. Осталось смен: {actor.state.switch_charges}"

    # =========================================================================
    # 2. РЕГИСТРАЦИЯ ХОДА (Multi-Pending)
    # =========================================================================

    async def register_move(
        self,
        actor_id: int,
        target_id: int | None,
        attack_zones: list[str] | None,
        block_zones: list[str] | None,
        ability_key: str | None = None,
    ) -> None:
        """
        Регистрирует ход.
        Если это ПЕРВАЯ заявка в паре — запускает таймер для ВТОРОГО (deadline).
        Если это ВТОРАЯ заявка — таймер удаляется (так как происходит расчет).
        """
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

        # 1. Формируем данные с Дедлайном
        # Дедлайн нужен, чтобы понять, когда эта заявка "протухнет",
        # если противник так и не ответит.
        deadline = int(time.time() + TURN_TIMEOUT)

        move_data = {
            "target_id": real_target_id,
            "attack": attack_zones,
            "block": block_zones,
            "ability": ability_key,
            "timestamp": time.time(),
            "deadline": deadline,  # 🔥 НОВОЕ: Таймер включен
        }
        move_json = json.dumps(move_data)

        # 2. Сохраняем
        await combat_manager.set_pending_move(self.session_id, actor_id, real_target_id, move_json)
        log.debug(f"Заявка {actor_id} -> {real_target_id} (Deadline: {deadline})")

        # 3. Проверяем совпадение
        counter_move_json = await combat_manager.get_pending_move(self.session_id, real_target_id, actor_id)

        if counter_move_json:
            # Пара совпала -> Расчет -> Таймеры больше не нужны для этой пары
            counter_move = json.loads(counter_move_json)

            await combat_manager.delete_pending_move(self.session_id, actor_id, real_target_id)
            await combat_manager.delete_pending_move(self.session_id, real_target_id, actor_id)

            await self._process_exchange(actor_id, move_data, real_target_id, counter_move)
            await self._process_ai_turns()

            # После обмена имеет смысл проверить, не истекло ли время у ДРУГИХ пар
            await self.check_deadlines()

        else:
            # Пары нет -> Мы ждем. Таймер тикает.
            # AI: Если цель бот, пинаем его.
            target_actor = await self._get_actor(real_target_id)
            if target_actor and target_actor.is_ai:
                decision = await CombatAIService.calculate_action(target_actor, self.session_id)
                if decision:
                    await self._process_ai_turns()

    # =========================================================================
    # 🛡️ КОНТРОЛЬ ТАЙМЕРОВ (Anti-AFK)
    # =========================================================================

    async def check_deadlines(self) -> None:
        """
        Проверяет все висящие заявки. Если время истекло — принудительно
        заставляет противника (того, кто молчит) сделать случайный ход.
        """
        # 1. Ищем ВСЕ заявки в этой сессии
        # (Это требует метода scan в combat_manager или получения всех ключей)
        # Для оптимизации пока пройдемся по участникам

        participants = await combat_manager.get_session_participants(self.session_id)
        now = time.time()

        for pid_str in participants:
            actor_id = int(pid_str)

            # Ищем заявки ОТ этого игрока К кому-то
            # Нам нужно найти тех, кто НЕ ответил.
            # То есть: A сделал заявку на B. Прошло 60 сек. B молчит.
            # Значит, надо пнуть B.

            # В Redis ключи устроены так: pending:ACTOR:TARGET
            # Мы не можем эффективно перебрать все пары без scan'а.
            # Допустим, мы знаем, что B - это targets[0] у A.

            actor = await self._get_actor(actor_id)
            if not actor or not actor.state or not actor.state.targets:
                continue

            target_id = actor.state.targets[0]

            # Есть ли заявка A -> B?
            pending_json = await combat_manager.get_pending_move(self.session_id, actor_id, target_id)
            if pending_json:
                data = json.loads(pending_json)
                deadline = data.get("deadline", 0)

                # Если время вышло
                if 0 < deadline < now:
                    log.warning(f"⏰ Таймер истек для пары {actor_id}->{target_id}. Принудительный ход {target_id}.")

                    # ПИНАЕМ ТОГО, КТО МОЛЧИТ (Target)
                    # Он должен ответить Актору
                    await self.register_move(
                        actor_id=target_id,
                        target_id=actor_id,
                        attack_zones=None,  # Рандом
                        block_zones=None,  # Рандом
                        ability_key=None,
                    )

    # =========================================================================
    # ЛОГИКА AI И ЗАВЕРШЕНИЯ (Обновлено)
    # =========================================================================

    async def _process_ai_turns(self) -> None:
        """
        Принудительно вызывает ход для всех живых NPC.
        """
        participants = await combat_manager.get_session_participants(self.session_id)
        for pid_str in participants:
            pid = int(pid_str)
            actor = await self._get_actor(pid)

            if not actor or not actor.is_ai or (actor.state and actor.state.hp_current <= 0):
                continue

            # 🔥 FIX: Передаем DTO объект целиком, чтобы AI мог проверить AbilityService
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
                ability_key=decision.get("ability"),  # Передаем выбранный скилл
            )

    # =========================================================================
    # СТАТИСТИКА И КОНТРОЛЬ БОЯ
    # =========================================================================

    def _update_stats(self, actor: CombatSessionContainerDTO, result_outgoing: dict, result_incoming: dict) -> None:
        """
        Обновляет статистику бойца на основе результатов раунда.
        """
        if not actor.state:
            return

        stats = actor.state.stats

        # 1. Исходящий урон (Мы ударили)
        dmg_dealt = result_outgoing.get("damage_total", 0)
        stats.damage_dealt += dmg_dealt

        # Хиты/Криты
        if result_outgoing.get("is_crit"):
            stats.crits_landed += 1

        # Вампиризм / Хил (из логов или result)
        # TODO: Если result содержит поле 'healing', добавить сюда
        stats.healing_done += result_outgoing.get("lifesteal", 0)

        # 2. Входящий (Нас ударили)
        dmg_taken = result_incoming.get("damage_total", 0)
        stats.damage_taken += dmg_taken

        if result_incoming.get("is_blocked"):
            stats.blocks_success += 1

        if result_incoming.get("is_dodged"):
            stats.dodges_success += 1

    async def _check_death_event(self, actor: CombatSessionContainerDTO) -> None:
        """Проверяет смерть и обновляет статус."""
        if actor.state and actor.state.hp_current <= 0:
            log.info(f"💀 Боец {actor.name} ({actor.char_id}) погиб.")
            # Тут можно отправить спец. сообщение в лог, если нужно
            # Но главное - это триггер для проверки конца боя

    async def _check_battle_end(self) -> bool:
        """
        Проверяет условия победы.
        Возвращает True, если бой закончен.
        """
        participants = await combat_manager.get_session_participants(self.session_id)

        teams_alive = set()

        for pid_str in participants:
            pid = int(pid_str)
            actor = await self._get_actor(pid)
            if not actor or not actor.state:
                continue

            if actor.state.hp_current > 0:
                teams_alive.add(actor.team)

        # Если осталась 1 команда (или 0 - ничья)
        if len(teams_alive) <= 1:
            winner_team = list(teams_alive)[0] if teams_alive else "none"
            await self._finish_battle(winner_team)
            return True

        return False

    async def _finish_battle(self, winner_team: str) -> None:
        """
        Финализация боя:
        1. Обновление мета-данных в Redis.
        2. Сбор статистики для аналитики и CSV.
        3. Запись логов в консоль.
        """
        log.info(f"🏆 БОЙ {self.session_id} ЗАВЕРШЕН. Победитель: {winner_team}")

        end_time = int(time.time())

        # 1. Получаем мета-данные (для длительности)
        meta = await combat_manager.get_session_meta(self.session_id)
        start_time = end_time
        if meta:
            start_time = int(meta.get("start_time", end_time))
        duration = max(0, end_time - start_time)

        # 2. Закрываем бой в Redis
        new_meta = {"active": 0, "winner": winner_team, "end_time": end_time}
        await combat_manager.create_session_meta(self.session_id, new_meta)

        # 3. Собираем данные (ОДИН цикл для всего)
        participants_ids = await combat_manager.get_session_participants(self.session_id)

        # Заготовка для CSV
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

            # А. Логируем в консоль (красиво)
            s = actor.state.stats
            log.info(
                f"📊 Stats {actor.name}: Dmg {s.damage_dealt}, Taken {s.damage_taken}, Blk {s.blocks_success}, HP {actor.state.hp_current}"
            )

            # Б. Обновляем макс. раунды (если этот боец прожил дольше всех)
            if actor.state.exchange_count > int(stats_payload["total_rounds"]):
                stats_payload["total_rounds"] = actor.state.exchange_count

            # В. Заполняем CSV-пейлоад (для первых двух бойцов p1/p2)
            if p_counter <= 2:
                prefix = f"p{p_counter}"
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

        # 4. Отправляем в аналитику (Fire and Forget)
        # Импортируем asyncio, если вдруг его не было в файле (он вроде был)
        import asyncio

        asyncio.create_task(analytics_service.log_combat_result(stats_payload))

        # TODO: [XP & REWARDS] - Начисление опыта и лута будет добавлено здесь позже

    # =========================================================================
    # 3. ЯДРО: РАСЧЕТ ОБМЕНА УДАРАМИ
    # =========================================================================

    async def _process_exchange(self, id_a: int, move_a: dict, id_b: int, move_b: dict) -> None:
        """
        Расчет раунда с поддержкой Ability Pipeline (Pre -> Calc -> Post).
        """
        log.debug(f"Начало обмена ударами между {id_a} и {id_b}.")
        actor_a = await self._get_actor(id_a)
        actor_b = await self._get_actor(id_b)

        if not actor_a or not actor_b or not actor_a.state or not actor_b.state:
            log.error("Критическая ошибка: данные бойцов не загружены.")
            return

        # 1. Агрегация статов
        stats_a = StatsCalculator.aggregate_all(actor_a.stats)
        stats_b = StatsCalculator.aggregate_all(actor_b.stats)

        # 2. Получение активных скиллов из хода
        skill_key_a = move_a.get("ability")
        skill_key_b = move_b.get("ability")

        # 3. Сборка Пайплайнов (Passive + Active)
        pipeline_a = AbilityService.get_full_pipeline(actor_a, skill_key_a)
        pipeline_b = AbilityService.get_full_pipeline(actor_b, skill_key_b)

        # 4. Получение базовых флагов (Rules)
        flags_a = dict(AbilityService.get_ability_rules(skill_key_a)) if skill_key_a else {}
        flags_b = dict(AbilityService.get_ability_rules(skill_key_b)) if skill_key_b else {}

        # ======================================================================
        # 🔥 ФАЗА 1: PRE-CALC (Модификация статов и флагов пайплайном)
        # ======================================================================
        AbilityService.execute_pre_calc(stats_a, flags_a, pipeline_a)
        AbilityService.execute_pre_calc(stats_b, flags_b, pipeline_b)

        # ======================================================================
        # 🎲 ФАЗА 2: CALCULATION (Ядро)
        # ======================================================================
        # A -> B
        res_a_to_b = CombatCalculator.calculate_hit(
            stats_atk=stats_a,
            stats_def=stats_b,
            current_shield=actor_b.state.energy_current,
            attack_zones=move_a["attack"],
            block_zones=move_b["block"],
            flags=flags_a,
        )

        # B -> A
        res_b_to_a = CombatCalculator.calculate_hit(
            stats_atk=stats_b,
            stats_def=stats_a,
            current_shield=actor_a.state.energy_current,
            attack_zones=move_b["attack"],
            block_zones=move_a["block"],
            flags=flags_b,
        )

        # ======================================================================
        # 🔥 ФАЗА 3: POST-CALC (Эффекты)
        # ======================================================================
        # Применяем эффекты пайплайна А (на основе результата удара по Б)
        AbilityService.execute_post_calc(res_a_to_b, actor_a, actor_b, pipeline_a)

        # Применяем эффекты пайплайна Б
        AbilityService.execute_post_calc(res_b_to_a, actor_b, actor_a, pipeline_b)

        # ======================================================================
        # ФИНАЛИЗАЦИЯ
        # ======================================================================

        # Списываем ресурсы за активные скиллы
        if skill_key_a:
            AbilityService.consume_resources(actor_a, skill_key_a)
        if skill_key_b:
            AbilityService.consume_resources(actor_b, skill_key_b)

        # Применяем итоговый урон и результаты
        self._apply_hit_result(actor_b, res_a_to_b)
        self._apply_hit_result(actor_a, res_b_to_a)

        self._apply_tokens(actor_a, res_a_to_b.get("tokens_atk", {}), res_b_to_a.get("tokens_def", {}))
        self._apply_tokens(actor_b, res_b_to_a.get("tokens_atk", {}), res_a_to_b.get("tokens_def", {}))

        self._apply_regen(actor_a, stats_a)
        self._apply_regen(actor_b, stats_b)

        actor_a.state.exchange_count += 1
        actor_b.state.exchange_count += 1

        # --- СТАТИСТИКА (Обновляем ДО сохранения) ---
        self._update_stats(actor_a, res_a_to_b, res_b_to_a)
        self._update_stats(actor_b, res_b_to_a, res_a_to_b)

        # --- СОХРАНЕНИЕ В REDIS (Один раз!) ---
        await combat_manager.save_actor_json(self.session_id, id_a, actor_a.model_dump_json())
        await combat_manager.save_actor_json(self.session_id, id_b, actor_b.model_dump_json())

        # --- ЛОГИ И СОБЫТИЯ ---
        await self._log_exchange(actor_a, res_a_to_b, actor_b, res_b_to_a)

        await self._check_death_event(actor_a)
        await self._check_death_event(actor_b)

        # Проверка конца боя
        if await self._check_battle_end():
            return

        log.info(f"Обмен {id_a} vs {id_b} завершен (Skill A: {skill_key_a}, Skill B: {skill_key_b}).")

    # =========================================================================
    # 4. ХЕЛПЕРЫ
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
