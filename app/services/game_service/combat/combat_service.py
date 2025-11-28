# app/services/game_service/combat/combat_service.py
import json
import random
import time
import uuid
from typing import Any

from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from app.resources.schemas_dto.combat_source_dto import (
    CombatSessionContainerDTO,
    FighterStateDTO,
    StatSourceData,
)
from app.services.core_service.manager.combat_manager import combat_manager
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


class CombatService:
    """
    Сервис-оркестратор боя.

    Управляет жизненным циклом боевой сессии, регистрацией участников,
    обработкой ходов и вызовом калькулятора для расчета результатов.
    """

    def __init__(self, session_id: str):
        """
        Инициализирует сервис для конкретной боевой сессии.

        Args:
            session_id (str): Уникальный идентификатор сессии.
        """
        self.session_id = session_id
        log.debug(f"CombatService инициализирован для сессии {session_id}")

    # =========================================================================
    # 1. ИНИЦИАЛИЗАЦИЯ БОЯ
    # =========================================================================

    @staticmethod
    async def create_battle(participants: list[dict], is_pve: bool = True) -> str:
        """
        Создает новую боевую сессию.

        Args:
            participants (list[dict]): Список участников (пока не используется).
            is_pve (bool): Является ли бой PvE.

        Returns:
            str: Уникальный ID созданной сессии.
        """
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
        """
        Добавляет участника в боевую сессию.

        Args:
            session (AsyncSession): Сессия базы данных.
            char_id (int): ID персонажа.
            team (str): Команда ('blue' или 'red').
            name (str): Имя персонажа.
            is_ai (bool): Является ли участник ИИ.
        """
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

        container.state = FighterStateDTO(hp_current=current_hp, energy_current=current_energy)
        log.debug(f"Боец {char_id} добавлен. HP: {current_hp}, Energy: {current_energy}")

        await combat_manager.add_participant_id(self.session_id, char_id)
        await combat_manager.save_actor_json(self.session_id, char_id, container.model_dump_json())
        log.info(f"Участник {name} ({char_id}) успешно добавлен в бой {self.session_id}.")

    async def add_dummy_participant(self, char_id: int, hp: int, energy: int, name: str) -> None:
        """Добавляет манекен/тень."""
        log.debug(f"Добавление Тени {name} ({char_id}) с {hp} HP / {energy} EN.")
        container = CombatSessionContainerDTO(char_id=char_id, team="red", name=name, is_ai=True)

        container.state = FighterStateDTO(hp_current=hp, energy_current=energy)

        container.stats["hp_max"] = StatSourceData(base=float(hp))
        container.stats["energy_max"] = StatSourceData(base=float(energy))
        container.stats["hp_regen"] = StatSourceData(base=0.0)

        await combat_manager.add_participant_id(self.session_id, char_id)
        await combat_manager.save_actor_json(self.session_id, char_id, container.model_dump_json())

    # =========================================================================
    # 2. РЕГИСТРАЦИЯ ХОДА
    # =========================================================================

    async def register_move(
        self,
        actor_id: int,
        target_id: int,
        attack_zones: list[str] | None,
        block_zones: list[str] | None,
    ) -> None:
        """Принимает ход. Если зоны не переданы, генерирует их случайно."""
        if not attack_zones:
            attack_zones = [random.choice(["head", "chest", "legs", "feet"])]
            log.debug(f"Боец {actor_id}: Авто-выбор атаки -> {attack_zones}")

        if not block_zones:
            block_zones = random.choice(VALID_BLOCK_PAIRS)
            log.debug(f"Боец {actor_id}: Авто-выбор защиты (Пара) -> {block_zones}")

        move_data = {
            "target_id": target_id,
            "attack": attack_zones,
            "block": block_zones,
            "timestamp": time.time(),
        }
        move_json = json.dumps(move_data)
        await combat_manager.set_pending_move(self.session_id, actor_id, move_json)

        target_actor = await self._get_actor(target_id)
        if target_actor and target_actor.is_ai:
            existing_ai_move = await combat_manager.get_pending_move(self.session_id, target_id)
            if not existing_ai_move:
                log.info(f"Цель {target_id} - AI. Вызываем CombatAIService.")
                ai_response = CombatAIService.generate_mob_response(target_id, attack_zones)
                ai_move_data = {
                    "target_id": actor_id,
                    "attack": ai_response["attack"],
                    "block": ai_response["block"],
                    "timestamp": time.time(),
                }
                await combat_manager.set_pending_move(self.session_id, target_id, json.dumps(ai_move_data))

        target_move_json = await combat_manager.get_pending_move(self.session_id, target_id)
        if target_move_json:
            target_move = json.loads(target_move_json)
            if int(target_move["target_id"]) == actor_id:
                should_calculate = (actor_id < target_id) or (target_actor and target_actor.is_ai)
                if should_calculate:
                    log.info(f"ПАРА СОВПАЛА. Расчет инициирован {actor_id}!")
                    await combat_manager.delete_pending_moves(self.session_id, actor_id, target_id)
                    await self._process_exchange(actor_id, move_data, target_id, target_move)
                else:
                    log.debug(f"Пара совпала, но расчет делегирован сопернику (ID {target_id}).")
            else:
                log.debug(f"Цель {target_id} бьет другого ({target_move['target_id']}). Ждем.")
        else:
            log.debug(f"Цель {target_id} еще не походила. Ждем.")

    # =========================================================================
    # 3. ЯДРО: РАСЧЕТ ОБМЕНА УДАРАМИ
    # =========================================================================

    async def _process_exchange(self, id_a: int, move_a: dict, id_b: int, move_b: dict) -> None:
        """Приватный метод для расчета взаимного обмена ударами."""
        log.debug(f"Начало обмена ударами между {id_a} и {id_b}.")
        actor_a = await self._get_actor(id_a)
        actor_b = await self._get_actor(id_b)

        if not actor_a or not actor_b or not actor_a.state or not actor_b.state:
            log.error(f"Критическая ошибка: не удалось загрузить состояние одного из бойцов ({id_a}, {id_b}).")
            return

        stats_a = StatsCalculator.aggregate_all(actor_a.stats)
        stats_b = StatsCalculator.aggregate_all(actor_b.stats)

        res_a_to_b = CombatCalculator.calculate_hit(
            stats_atk=stats_a,
            stats_def=stats_b,
            current_shield=actor_b.state.energy_current,
            attack_zones=move_a["attack"],
            block_zones=move_b["block"],
        )
        res_b_to_a = CombatCalculator.calculate_hit(
            stats_atk=stats_b,
            stats_def=stats_a,
            current_shield=actor_a.state.energy_current,
            attack_zones=move_b["attack"],
            block_zones=move_a["block"],
        )

        # TODO: [NEXT SESSION] СТАТИСТИКА
        # 1. Обновить статистику Actor A:
        #    - total_damage_dealt += res_a_to_b['damage_total']
        #    - total_damage_blocked += res_a_to_b['damage_blocked_by_enemy'] (если будем считать)
        #    - hits_landed += 1 (если урон > 0)
        # 2. То же самое для Actor B.
        # Эти данные нужно хранить в fighter_state или отдельном поле stats внутри DTO.

        self._apply_hit_result(actor_b, res_a_to_b)
        self._apply_hit_result(actor_a, res_b_to_a)

        self._apply_tokens(actor_a, res_a_to_b.get("tokens_atk", {}), res_b_to_a.get("tokens_def", {}))
        self._apply_tokens(actor_b, res_b_to_a.get("tokens_atk", {}), res_a_to_b.get("tokens_def", {}))

        self._apply_regen(actor_a, stats_a)
        self._apply_regen(actor_b, stats_b)
        actor_a.state.exchange_count += 1
        actor_b.state.exchange_count += 1

        await combat_manager.save_actor_json(self.session_id, id_a, actor_a.model_dump_json())
        await combat_manager.save_actor_json(self.session_id, id_b, actor_b.model_dump_json())

        await self._log_exchange(actor_a, res_a_to_b, actor_b, res_b_to_a)

        # TODO: [NEXT SESSION] KILL FEED
        # Если actor_b умер -> записать в статистику Actor A "kills += 1"

        await self._check_death_event(actor_a)
        await self._check_death_event(actor_b)

        # TODO: [NEXT SESSION] CHECK WIN CONDITION
        # Вызвать метод self._check_battle_end(session_id)
        # Если одна из команд мертва -> Завершить бой.

        log.info(f"Обмен ударами между {id_a} и {id_b} завершен.")

    # =========================================================================
    # 4. ХЕЛПЕРЫ
    # =========================================================================

    def _apply_hit_result(self, actor: CombatSessionContainerDTO, result: dict) -> None:
        """Применяет урон и вампиризм к состоянию бойца."""
        if not actor.state:
            return
        actor.state.energy_current = max(0, actor.state.energy_current - result["shield_dmg"])
        actor.state.hp_current = max(0, actor.state.hp_current - result["hp_dmg"])
        if result["hp_dmg"] > 0 and actor.state.hp_current <= 0:
            result["logs"].append("💀 <b>Удар добил противника!</b>")

    def _apply_tokens(self, actor: CombatSessionContainerDTO, atk_tokens: dict, def_tokens: dict) -> None:
        """Суммирует полученные токены в состояние бойца."""
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
        """Формирует и сохраняет лог обмена ударами в Redis."""
        log.debug(f"Формирование лога для обмена между {actor_a.name} и {actor_b.name}.")
        combined_logs = []

        text_a = CombatLogBuilder.build_log_entry(actor_a.name, actor_b.name, res_a)
        combined_logs.append(text_a)
        log.debug(f"Лог атаки {actor_a.name}: {text_a}")

        text_b = CombatLogBuilder.build_log_entry(actor_b.name, actor_a.name, res_b)
        combined_logs.append(text_b)
        log.debug(f"Лог атаки {actor_b.name}: {text_b}")

        log_entry: dict[str, Any] = {
            "time": time.time(),
            "round_index": actor_a.state.exchange_count if actor_a.state else 0,
            "pair_names": [actor_a.name, actor_b.name],
            "logs": combined_logs,
        }

        await combat_manager.push_combat_log(self.session_id, json.dumps(log_entry))
        log.debug(f"Запись лога для раунда {log_entry['round_index']} сохранена в Redis.")

    def _apply_regen(self, actor: CombatSessionContainerDTO, stats: dict[str, float]) -> None:
        """Применяет регенерацию HP и энергии в конце хода."""
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
        """Получает и десериализует состояние бойца из Redis."""
        data = await combat_manager.get_actor_json(self.session_id, char_id)
        if data:
            try:
                return CombatSessionContainerDTO.model_validate_json(data)
            except json.JSONDecodeError as e:
                log.exception(f"Ошибка десериализации данных для char_id={char_id}: {e}")
                return None
        log.warning(f"Не найдены данные для бойца {char_id} в сессии {self.session_id}.")
        return None

    async def _check_death_event(self, actor: CombatSessionContainerDTO) -> None:
        """Проверяет, умер ли боец, и логирует это событие."""
        if actor.state and actor.state.hp_current <= 0:
            log.info(f"Боец {actor.name} ({actor.char_id}) в сессии {self.session_id} погиб.")
            # TODO: Отправить отдельное событие в лог "💀 Имя погибает!"

    # TODO: [NEXT SESSION] NEW METHOD: _finish_battle
    # async def _finish_battle(self, winner_team: str):
    #     1. Собрать все логи из Redis (lrange).
    #     2. Собрать итоговую статистику участников.
    #     3. Создать запись в SQL таблице `combat_history` (JSON field).
    #     4. Начислить опыт и лут победителям.
    #     5. Очистить Redis (удалить ключи сессии).
    #     6. Отправить финальное сообщение в UI (Победа/Поражение + Кнопка "Выйти").
