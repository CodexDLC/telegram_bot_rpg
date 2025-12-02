# app/services/game_service/combat/combat_service.py
import json
import time
from typing import Any

from loguru import logger as log
from pydantic import ValidationError

from app.resources.schemas_dto.combat_source_dto import CombatSessionContainerDTO
from app.services.core_service.manager.combat_manager import combat_manager
from app.services.game_service.combat.ability_service import AbilityService
from app.services.game_service.combat.combat_ai_service import CombatAIService
from app.services.game_service.combat.combat_calculator import CombatCalculator
from app.services.game_service.combat.combat_lifecycle_service import CombatLifecycleService
from app.services.game_service.combat.combat_log_builder import CombatLogBuilder
from app.services.game_service.combat.combat_turn_manager import CombatTurnManager
from app.services.game_service.combat.combat_xp_manager import CombatXPManager
from app.services.game_service.combat.stats_calculator import StatsCalculator
from app.services.game_service.combat.victory_checker import VictoryChecker


class CombatService:
    """
    Runtime-Сервис боя.
    Отвечает ТОЛЬКО за обработку ходов и расчет результатов.
    Созданием и завершением боя занимается CombatLifecycleService.
    """

    def __init__(self, session_id: str):
        """
        Args:
            session_id: Идентификатор сессии боя.
        """
        self.session_id = session_id
        self.turn_manager = CombatTurnManager(session_id)
        log.info(f"CombatServiceInit | session_id={session_id}")

    # =========================================================================
    # УПРАВЛЕНИЕ ЦЕЛЯМИ (Runtime State)
    # =========================================================================

    async def switch_target(self, actor_id: int, new_target_id: int) -> tuple[bool, str]:
        """
        Смена цели во время боя.

        Args:
            actor_id: ID атакующего.
            new_target_id: ID новой цели.

        Returns:
            Кортеж (успех, сообщение).
        """
        log.info(f"TargetSwitch | actor_id={actor_id} new_target_id={new_target_id} session_id={self.session_id}")
        actor = await self._get_actor(actor_id)
        if not actor or not actor.state:
            log.warning(f"TargetSwitchFail | reason=no_actor actor_id={actor_id} session_id={self.session_id}")
            return False, "Ошибка данных."

        if not actor.state.targets or new_target_id not in actor.state.targets:
            log.warning(
                f"TargetSwitchFail | reason=invalid_target actor_id={actor_id} new_target_id={new_target_id} session_id={self.session_id}"
            )
            return False, "Недопустимая цель."

        if actor.state.targets[0] == new_target_id:
            log.warning(
                f"TargetSwitchFail | reason=target_already_selected actor_id={actor_id} new_target_id={new_target_id} session_id={self.session_id}"
            )
            return False, "Эта цель уже выбрана."

        if actor.state.switch_charges <= 0:
            log.warning(f"TargetSwitchFail | reason=no_switch_charges actor_id={actor_id} session_id={self.session_id}")
            return False, "Не хватает очков тактики."

        actor.state.switch_charges -= 1

        # Ротация
        try:
            idx = actor.state.targets.index(new_target_id)
            actor.state.targets[0], actor.state.targets[idx] = (actor.state.targets[idx], actor.state.targets[0])
        except ValueError:
            log.error(
                f"TargetSwitchError | reason=value_error actor_id={actor_id} new_target_id={new_target_id} targets={actor.state.targets}",
                exc_info=True,
            )
            return False, "Ошибка списка."

        await combat_manager.save_actor_json(self.session_id, actor_id, actor.model_dump_json())
        log.info(
            f"TargetSwitchSuccess | actor_id={actor_id} new_target_id={new_target_id} charges_left={actor.state.switch_charges}"
        )
        return True, f"Цель изменена. Осталось смен: {actor.state.switch_charges}"

    # =========================================================================
    # РЕГИСТРАЦИЯ И РАСЧЕТ ХОДА
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
        Регистрирует ход игрока и запускает расчет, если оба хода сделаны.
        """
        log.debug(f"RegisterMove | actor_id={actor_id} target_id={target_id} session_id={self.session_id}")
        actor = await self._get_actor(actor_id)
        if not actor or not actor.state:
            log.warning(f"RegisterMoveFail | reason=no_actor actor_id={actor_id} session_id={self.session_id}")
            return

        real_target_id = target_id
        if real_target_id is None:
            if actor.state.targets:
                real_target_id = actor.state.targets[0]
            else:
                log.warning(f"RegisterMoveFail | reason=no_target actor_id={actor_id} session_id={self.session_id}")
                return

        # 1. Делегируем TurnManager
        exchange_data = await self.turn_manager.register_move_request(
            actor_id, real_target_id, attack_zones, block_zones, ability_key
        )

        # 2. Если пара есть -> Расчет
        if exchange_data:
            log.info(f"ExchangePairReady | actor_a={actor_id} actor_b={real_target_id} session_id={self.session_id}")
            await self._process_exchange(
                actor_id, exchange_data["my_move"], real_target_id, exchange_data["enemy_move"]
            )
            await self._process_ai_turns()
            await self.check_deadlines()
        else:
            # Если пары нет, проверяем AI
            target_actor = await self._get_actor(real_target_id)
            if target_actor and target_actor.is_ai:
                log.debug(f"CheckingAIAction | ai_actor_id={real_target_id} session_id={self.session_id}")
                decision = await CombatAIService.calculate_action(target_actor, self.session_id)
                if decision:
                    await self._process_ai_turns()

    async def check_deadlines(self) -> None:
        """
        Проверяет и обрабатывает истекшие таймеры ходов.
        """
        participants = await combat_manager.get_session_participants(self.session_id)
        actors_map: dict[int, CombatSessionContainerDTO] = {}
        for pid in participants:
            actor = await self._get_actor(int(pid))
            if actor:
                actors_map[int(pid)] = actor

        expired_list = await self.turn_manager.check_expired_deadlines(actors_map)

        for lazy_id, agg_id in expired_list:
            log.warning(f"DeadlineExpired | lazy_actor_id={lazy_id} opponent_id={agg_id} session_id={self.session_id}")
            await self.register_move(
                actor_id=lazy_id, target_id=agg_id, attack_zones=None, block_zones=None, ability_key=None
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

            log.info(f"AIProcessingTurn | actor_id={pid} target_id={target_id} session_id={self.session_id}")
            await self.register_move(
                actor_id=pid,
                target_id=target_id,
                attack_zones=decision["attack"],
                block_zones=decision["block"],
                ability_key=decision.get("ability"),
            )

    # =========================================================================
    # ЯДРО РАСЧЕТА (Без изменений логики, только вызовы)
    # =========================================================================

    async def _process_exchange(self, id_a: int, move_a: dict, id_b: int, move_b: dict) -> None:
        log.debug(f"ProcessExchange | actor_a={id_a} actor_b={id_b} session_id={self.session_id}")
        actor_a = await self._get_actor(id_a)
        actor_b = await self._get_actor(id_b)

        if not actor_a or not actor_b or not actor_a.state or not actor_b.state:
            log.error(
                f"ProcessExchangeFail | reason=actor_data_missing a_id={id_a} b_id={id_b} session_id={self.session_id}"
            )
            return

        stats_a = StatsCalculator.aggregate_all(actor_a.stats)
        stats_b = StatsCalculator.aggregate_all(actor_b.stats)

        # Pipelines
        sk_a = move_a.get("ability")
        sk_b = move_b.get("ability")
        pipe_a = AbilityService.get_full_pipeline(actor_a, sk_a)
        pipe_b = AbilityService.get_full_pipeline(actor_b, sk_b)
        flags_a = dict(AbilityService.get_ability_rules(sk_a)) if sk_a else {}
        flags_b = dict(AbilityService.get_ability_rules(sk_b)) if sk_b else {}

        # Pre-Calc
        AbilityService.execute_pre_calc(stats_a, flags_a, pipe_a)
        AbilityService.execute_pre_calc(stats_b, flags_b, pipe_b)

        # Calculation
        # Calculation
        res_a = CombatCalculator.calculate_hit(
            stats_a, stats_b, actor_b.state.energy_current, move_a["attack"], move_b["block"], flags=flags_a
        )
        res_b = CombatCalculator.calculate_hit(
            stats_b, stats_a, actor_a.state.energy_current, move_b["attack"], move_a["block"], flags=flags_b
        )

        # Post-Calc
        AbilityService.execute_post_calc(res_a, actor_a, actor_b, pipe_a)
        AbilityService.execute_post_calc(res_b, actor_b, actor_a, pipe_b)

        if sk_a:
            AbilityService.consume_resources(actor_a, sk_a)
        if sk_b:
            AbilityService.consume_resources(actor_b, sk_b)

        # XP & Stats
        self._register_xp_events(actor_a, res_a, res_b)
        self._register_xp_events(actor_b, res_b, res_a)

        self._apply_results(actor_b, res_a)
        self._apply_results(actor_a, res_b)

        # 🔥 НОВЫЙ КОД: ПРИМЕНЕНИЕ ОТРАЖЕННОГО УРОНА
        self._apply_thorns_damage(actor_a, res_b)  # Урон от блока B идет к А
        self._apply_thorns_damage(actor_b, res_a)  # Урон от блока A идет к B

        self._apply_regen(actor_a, stats_a)
        self._apply_regen(actor_b, stats_b)

        actor_a.state.exchange_count += 1
        actor_b.state.exchange_count += 1

        self._update_stats(actor_a, res_a, res_b)
        self._update_stats(actor_b, res_b, res_a)

        # Save & Log
        await combat_manager.save_actor_json(self.session_id, id_a, actor_a.model_dump_json())
        await combat_manager.save_actor_json(self.session_id, id_b, actor_b.model_dump_json())
        await self._log_exchange(actor_a, res_a, actor_b, res_b)

        # Check End
        if await self._check_battle_end():
            return

    # --- Приватные методы ---

    def _apply_thorns_damage(self, actor: CombatSessionContainerDTO, res: dict):
        """Применяет отраженный урон к актору."""
        if not actor.state:
            return

        thorns_damage = res.get("thorns_damage", 0)
        if thorns_damage > 0:
            actor.state.hp_current = max(0, actor.state.hp_current - thorns_damage)
            log.debug(f"ThornsApplied | char_id={actor.char_id} damage={thorns_damage}")

    def _apply_results(self, actor: CombatSessionContainerDTO, res: dict):
        if not actor.state:
            return
        actor.state.energy_current = max(0, actor.state.energy_current - res["shield_dmg"])
        actor.state.hp_current = max(0, actor.state.hp_current - res["hp_dmg"])
        if res["hp_dmg"] > 0 and actor.state.hp_current <= 0:
            res["logs"].append("💀 <b>Удар добил противника!</b>")

        # Tokens
        for t, c in res.get("tokens_atk", {}).items():
            actor.state.tokens[t] = actor.state.tokens.get(t, 0) + c
        for t, c in res.get("tokens_def", {}).items():
            actor.state.tokens[t] = actor.state.tokens.get(t, 0) + c

    def _apply_regen(self, actor: CombatSessionContainerDTO, stats: dict):
        if not actor.state or actor.state.hp_current <= 0:
            return
        max_hp = int(stats.get("hp_max", 1.0))
        max_en = int(stats.get("energy_max", 0.0))
        actor.state.hp_current = min(max_hp, actor.state.hp_current + int(stats.get("hp_regen", 0.0)))
        actor.state.energy_current = min(max_en, actor.state.energy_current + int(stats.get("energy_regen", 0.0)))

    def _update_stats(self, actor: CombatSessionContainerDTO, out: dict, inc: dict):
        if not actor.state:
            return
        s = actor.state.stats
        s.damage_dealt += out.get("damage_total", 0)
        if out.get("is_crit"):
            s.crits_landed += 1
        s.healing_done += out.get("lifesteal", 0)
        s.damage_taken += inc.get("damage_total", 0)
        if inc.get("is_blocked"):
            s.blocks_success += 1
        if inc.get("is_dodged"):
            s.dodges_success += 1

    async def _log_exchange(
        self,
        actor_a: CombatSessionContainerDTO,
        res_a: dict,
        actor_b: CombatSessionContainerDTO,
        res_b: dict,
    ) -> None:
        if not actor_a.state or not actor_b.state:
            return

        combined_logs = []

        # Атака A -> B (Показываем остаток HP у B)
        text_a = CombatLogBuilder.build_log_entry(
            actor_a.name,
            actor_b.name,
            res_a,
            defender_hp=actor_b.state.hp_current,
            defender_energy=actor_b.state.energy_current,
        )

        combined_logs.append(text_a)

        # Атака B -> A (Показываем остаток HP у A)
        text_b = CombatLogBuilder.build_log_entry(
            actor_b.name,
            actor_a.name,
            res_b,
            defender_hp=actor_a.state.hp_current,
            defender_energy=actor_a.state.energy_current,
        )
        combined_logs.append(text_b)

        log_entry: dict[str, Any] = {
            "time": time.time(),
            "round_index": actor_a.state.exchange_count,
            "pair_names": [actor_a.name, actor_b.name],
            "logs": combined_logs,
        }
        await combat_manager.push_combat_log(self.session_id, json.dumps(log_entry))

    async def _check_battle_end(self) -> bool:
        """Делегируем проверку победы."""
        p_ids = await combat_manager.get_session_participants(self.session_id)
        actors: dict[int, CombatSessionContainerDTO] = {}
        for pid in p_ids:
            actor = await self._get_actor(int(pid))
            if actor:
                actors[int(pid)] = actor

        winner = VictoryChecker.check_battle_end(actors)
        if winner:
            log.info(f"BattleEnd | winner_team={winner} session_id={self.session_id}")
            # 🔥 ВЫЗОВ LIFECYCLE
            await CombatLifecycleService.finish_battle(self.session_id, winner)
            return True
        return False

    async def process_turn_updates(self) -> None:
        """
        Обрабатывает все необходимые обновления боя: ход AI и проверку Deadlines.
        (Публичный метод-обёртка для вызова из Хэндлеров)
        """
        await self._process_ai_turns()
        await self.check_deadlines()

    async def _get_actor(self, char_id: int) -> CombatSessionContainerDTO | None:
        data = await combat_manager.get_actor_json(self.session_id, char_id)
        if data:
            try:
                return CombatSessionContainerDTO.model_validate_json(data)
            except json.JSONDecodeError:
                log.exception(
                    f"ActorParseFail | reason=json_decode_error char_id={char_id} session_id={self.session_id} data='{data}'",
                    exc_info=True,
                )
                return None
            except ValidationError:
                log.exception(
                    f"ActorParseFail | reason=validation_error char_id={char_id} session_id={self.session_id} data='{data}'",
                    exc_info=True,
                )
                return None
        log.warning(f"ActorNotFound | char_id={char_id} session_id={self.session_id}")
        return None

    @staticmethod
    def _get_item_subtype_by_type(actor: CombatSessionContainerDTO, item_type: str) -> str | None:
        """Ищет предмет определенного типа и возвращает его подтип."""
        for item in actor.equipped_items:
            if item.item_type.value == item_type:
                return item.subtype
        return None

    @staticmethod
    def _register_xp_events(actor: CombatSessionContainerDTO, outgoing: dict, incoming: dict) -> None:
        """
        Регистрирует опыт за действия в раунде, проверяя экипировку.
        """
        # 1. АТАКУЮЩИЙ ОПЫТ (Оружие)
        outcome = "success"
        if outgoing["is_dodged"]:
            outcome = "miss"
        elif outgoing["is_blocked"]:
            outcome = "partial"
        elif outgoing["is_crit"]:
            outcome = "crit"

        # NOTE: Предполагаем, что если нет оружия, идет melee_combat XP
        CombatXPManager.register_action(actor, "sword", outcome)

        # 2. ПАССИВНЫЙ ОПЫТ (Броня) - если получен урон
        if incoming["damage_total"] > 0:
            # 🔥 ИСПРАВЛЕНО: Проверяем, есть ли броня (и берем ее тип)
            armor_subtype = CombatService._get_item_subtype_by_type(actor, "armor")
            if armor_subtype:
                # Начисление XP по типу надетой брони (light, medium, heavy)
                CombatXPManager.register_action(actor, armor_subtype, "success")

        # 3. ЩИТ - если блок сработал
        if incoming["is_blocked"]:
            # 🔥 ИСПРАВЛЕНО: Проверяем, есть ли щит/аксессуар с тегом 'shield'
            shield_subtype = CombatService._get_item_subtype_by_type(actor, "shield")  # Subtype "shield"

            # NOTE: Используем существующий механизм блокировки (shield_skill)
            if shield_subtype == "shield" or incoming["block_type"] == "passive":
                CombatXPManager.register_action(actor, "shield", "success")
