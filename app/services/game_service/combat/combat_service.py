# app/services/game_service/combat/combat_service.py
import json
import time
import uuid

from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from app.resources.schemas_dto.combat_source_dto import CombatSessionContainerDTO
from app.services.core_service.manager.combat_manager import combat_manager
from app.services.game_service.combat.combat_aggregator import CombatAggregator
from app.services.game_service.combat.combat_calculator import CombatCalculator
from app.services.game_service.combat.stats_calculator import StatsCalculator


class CombatService:
    """
    Оркестратор боя.
    Управляет сессией, ходами и вызывает математику.
    """

    def __init__(self, session_id: str):
        self.session_id = session_id

    # =========================================================================
    # 1. ИНИЦИАЛИЗАЦИЯ
    # =========================================================================

    @staticmethod
    async def create_battle(participants: list[dict], is_pve: bool = True) -> str:
        session_id = str(uuid.uuid4())

        meta_data = {"start_time": int(time.time()), "is_pve": int(is_pve), "active": 1}
        await combat_manager.create_session_meta(session_id, meta_data)

        log.info(f"Бой {session_id} создан. Участников: {len(participants)}")
        return session_id

    async def add_participant(self, session: AsyncSession, char_id: int, team: str, name: str, is_ai: bool = False):
        aggregator = CombatAggregator(session)
        container = await aggregator.collect_session_container(char_id)

        container.team = team
        container.name = name
        container.is_ai = is_ai

        # TODO: Здесь можно добавить загрузку текущего HP из БД, если оно не полное

        await combat_manager.save_actor_json(self.session_id, char_id, container.model_dump_json())

    # =========================================================================
    # 2. ХОД ИГРОКА
    # =========================================================================

    async def register_move(self, actor_id: int, target_id: int, attack_zones: list[str], block_zones: list[str]):
        # 1. Сохраняем заявку
        move_data = {"target_id": target_id, "attack": attack_zones, "block": block_zones, "timestamp": time.time()}
        move_json = json.dumps(move_data)

        await combat_manager.set_pending_move(self.session_id, actor_id, move_json)
        log.debug(f"Боец {actor_id} заявил атаку на {target_id}.")

        # 2. Проверяем встречную заявку
        target_move_json = await combat_manager.get_pending_move(self.session_id, target_id)

        if target_move_json:
            target_move = json.loads(target_move_json)
            # Если цель тоже бьет нас -> Расчет
            if int(target_move["target_id"]) == actor_id:
                log.info(f"ПАРА СОВПАЛА: {actor_id} <-> {target_id}. Расчет!")

                await combat_manager.delete_pending_moves(self.session_id, actor_id, target_id)
                await self._process_exchange(actor_id, move_data, target_id, target_move)
            else:
                log.debug(f"Цель {target_id} занята другим ({target_move['target_id']}). Ждем.")
        else:
            log.debug(f"Цель {target_id} еще не походила. Ждем.")

    # =========================================================================
    # 3. ЯДРО: РАСЧЕТ ОБМЕНА
    # =========================================================================

    async def _process_exchange(self, id_a: int, move_a: dict, id_b: int, move_b: dict):
        # 1. Загрузка
        actor_a = await self._get_actor(id_a)
        actor_b = await self._get_actor(id_b)

        if not actor_a or not actor_b or not actor_a.state or not actor_b.state:
            log.error("Ошибка состояния бойцов.")
            return

        # 2. Агрегация (DTO -> Числа)
        stats_a = StatsCalculator.aggregate_all(actor_a.stats)
        stats_b = StatsCalculator.aggregate_all(actor_b.stats)

        # 3. Расчет ударов (Математика)
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

        # 4. Применение урона и ПРОВЕРКА СМЕРТИ (для логов)

        # --- Урон по B ---
        actor_b.state.energy_current = max(0, actor_b.state.energy_current - res_a_to_b["shield_dmg"])
        actor_b.state.hp_current = max(0, actor_b.state.hp_current - res_a_to_b["hp_dmg"])

        if actor_b.state.hp_current <= 0:
            # Добавляем в логи АТАКИ (А убил Б)
            res_a_to_b["logs"].append("💀 <b>Удар добил противника!</b>")

        # --- Урон по A ---
        actor_a.state.energy_current = max(0, actor_a.state.energy_current - res_b_to_a["shield_dmg"])
        actor_a.state.hp_current = max(0, actor_a.state.hp_current - res_b_to_a["hp_dmg"])

        if actor_a.state.hp_current <= 0:
            # Добавляем в логи АТАКИ (Б убил А)
            res_b_to_a["logs"].append("💀 <b>Удар добил противника!</b>")

        # 5. Регенерация (Только для живых)
        self._apply_regen(actor_a, stats_a)
        self._apply_regen(actor_b, stats_b)

        # Счетчики
        actor_a.state.exchange_count += 1
        actor_b.state.exchange_count += 1

        # 6. Сохранение
        await combat_manager.save_actor_json(self.session_id, id_a, actor_a.model_dump_json())
        await combat_manager.save_actor_json(self.session_id, id_b, actor_b.model_dump_json())

        # 7. Логирование (уже с фразами о смерти)
        await self._log_exchange(actor_a, res_a_to_b, actor_b, res_b_to_a)

        # 8. Техническое завершение (флаги, эвенты)
        await self._check_death_event(actor_a)
        await self._check_death_event(actor_b)

    # =========================================================================
    # ХЕЛПЕРЫ
    # =========================================================================

    async def _log_exchange(
        self, actor_a: CombatSessionContainerDTO, res_a: dict, actor_b: CombatSessionContainerDTO, res_b: dict
    ) -> None:
        combined_logs = []

        combined_logs.append(f"⚔️ <b>{actor_a.name}</b>:")
        combined_logs.extend(res_a["logs"])
        combined_logs.append("")  # Пустая строка

        combined_logs.append(f"⚔️ <b>{actor_b.name}</b>:")
        combined_logs.extend(res_b["logs"])

        log_entry = {
            "time": time.time(),
            "round_index": actor_a.state.exchange_count if actor_a.state else 0,
            "pair_names": [actor_a.name, actor_b.name],
            "logs": combined_logs,
        }
        await combat_manager.push_combat_log(self.session_id, json.dumps(log_entry))

    def _apply_regen(self, actor: CombatSessionContainerDTO, stats: dict[str, float]) -> None:
        if not actor.state or actor.state.hp_current <= 0:
            return

        # HP Regen
        regen_hp = int(stats.get("hp_regen", 0))
        max_hp = int(stats.get("hp_max", 1))
        if regen_hp > 0 and actor.state.hp_current < max_hp:
            actor.state.hp_current = min(max_hp, actor.state.hp_current + regen_hp)

        # Energy Regen
        regen_en = int(stats.get("energy_regen", 0))
        max_en = int(stats.get("energy_max", 0))
        if regen_en > 0 and actor.state.energy_current < max_en:
            actor.state.energy_current = min(max_en, actor.state.energy_current + regen_en)

    async def _get_actor(self, char_id: int) -> CombatSessionContainerDTO | None:
        data = await combat_manager.get_actor_json(self.session_id, char_id)
        if data:
            return CombatSessionContainerDTO.model_validate_json(data)
        return None

    async def _check_death_event(self, actor: CombatSessionContainerDTO):
        """Техническая обработка смерти (удаление из очередей, начисление опыта)."""
        if actor.state and actor.state.hp_current <= 0:
            log.info(f"Боец {actor.name} ({actor.char_id}) официально мертв. Запуск Death Event.")
            # TODO: Здесь будет логика лута, опыта и удаления сессии
