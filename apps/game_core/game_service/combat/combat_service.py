import json
import time
from typing import Any

from loguru import logger as log
from pydantic import ValidationError

from apps.common.schemas_dto import CombatSessionContainerDTO
from apps.common.services.core_service import CombatManager
from apps.common.services.core_service.manager.account_manager import AccountManager
from apps.game_core.game_service.combat.ability_service import AbilityService
from apps.game_core.game_service.combat.combat_calculator import CombatCalculator
from apps.game_core.game_service.combat.combat_lifecycle_service import CombatLifecycleService
from apps.game_core.game_service.combat.combat_log_builder import CombatLogBuilder
from apps.game_core.game_service.combat.combat_xp_manager import CombatXPManager
from apps.game_core.game_service.combat.consumable_service import ConsumableService
from apps.game_core.game_service.combat.stats_calculator import StatsCalculator
from apps.game_core.game_service.combat.victory_checker import VictoryChecker


class CombatService:
    """
    Runtime-сервис боя, отвечающий за обработку ходов и расчет результатов.
    """

    def __init__(self, session_id: str, combat_manager: CombatManager, account_manager: AccountManager):
        self.session_id = session_id
        self.combat_manager = combat_manager
        self.account_manager = account_manager
        self.lifecycle_service = CombatLifecycleService(combat_manager, account_manager)

    async def use_consumable(self, actor_id: int, item_id: int) -> tuple[bool, str]:
        actor = await self._get_actor(actor_id)
        if not actor:
            return False, "Ошибка данных актора."

        success, msg = ConsumableService.use_item(actor, item_id)

        if success:
            await self.combat_manager.set_rbc_actor_state_json(self.session_id, actor_id, actor.model_dump_json())

        return success, msg

    async def switch_target(self, actor_id: int, new_target_id: int) -> tuple[bool, str]:
        actor = await self._get_actor(actor_id)
        if not actor or not actor.state:
            return False, "Ошибка данных."

        if not actor.state.targets or new_target_id not in actor.state.targets:
            return False, "Недопустимая цель."

        if actor.state.targets[0] == new_target_id:
            return False, "Эта цель уже выбрана."

        if actor.state.switch_charges <= 0:
            return False, "Не хватает очков тактики."

        actor.state.switch_charges -= 1

        try:
            idx = actor.state.targets.index(new_target_id)
            actor.state.targets[0], actor.state.targets[idx] = (actor.state.targets[idx], actor.state.targets[0])
        except ValueError:
            return False, "Ошибка списка."

        await self.combat_manager.set_rbc_actor_state_json(self.session_id, actor_id, actor.model_dump_json())
        return True, f"Цель изменена. Осталось смен: {actor.state.switch_charges}"

    async def process_exchange(self, id_a: int, move_a: dict, id_b: int, move_b: dict) -> None:
        log.debug(
            f"CombatService | action=process_exchange actor_a={id_a} actor_b={id_b} session_id='{self.session_id}'"
        )
        actor_a = await self._get_actor(id_a)
        actor_b = await self._get_actor(id_b)

        if not actor_a or not actor_b or not actor_a.state or not actor_b.state:
            return

        stats_a = StatsCalculator.aggregate_all(actor_a.stats)
        stats_b = StatsCalculator.aggregate_all(actor_b.stats)

        sk_a = move_a.get("ability")
        sk_b = move_b.get("ability")
        pipe_a = AbilityService.get_full_pipeline(actor_a, sk_a)
        pipe_b = AbilityService.get_full_pipeline(actor_b, sk_b)
        flags_a = dict(AbilityService.get_ability_rules(sk_a)) if sk_a else {}
        flags_b = dict(AbilityService.get_ability_rules(sk_b)) if sk_b else {}

        AbilityService.execute_pre_calc(stats_a, flags_a, pipe_a)
        AbilityService.execute_pre_calc(stats_b, flags_b, pipe_b)

        res_a = CombatCalculator.calculate_hit(
            stats_a, stats_b, actor_b.state.energy_current, move_a["attack"], move_b["block"], flags=flags_a
        )
        res_b = CombatCalculator.calculate_hit(
            stats_b, stats_a, actor_a.state.energy_current, move_b["attack"], move_a["block"], flags=flags_b
        )

        AbilityService.execute_post_calc(res_a, actor_a, actor_b, pipe_a)
        AbilityService.execute_post_calc(res_b, actor_b, actor_a, pipe_b)

        if sk_a:
            AbilityService.consume_resources(actor_a, sk_a)
        if sk_b:
            AbilityService.consume_resources(actor_b, sk_b)

        self._register_xp_events(actor_a, res_a, res_b)
        self._register_xp_events(actor_b, res_b, res_a)

        self._apply_results(actor_b, res_a)
        self._apply_results(actor_a, res_b)

        self._apply_thorns_damage(actor_a, res_b)
        self._apply_thorns_damage(actor_b, res_a)

        self._apply_regen(actor_a, stats_a)
        self._apply_regen(actor_b, stats_b)

        actor_a.state.exchange_count += 1
        actor_b.state.exchange_count += 1

        self._update_stats(actor_a, res_a, res_b)
        self._update_stats(actor_b, res_b, res_a)

        await self.combat_manager.set_rbc_actor_state_json(self.session_id, id_a, actor_a.model_dump_json())
        await self.combat_manager.set_rbc_actor_state_json(self.session_id, id_b, actor_b.model_dump_json())
        await self._log_exchange(actor_a, res_a, actor_b, res_b)

        # Ротация очереди после боя
        await self._rotate_queues(actor_a, actor_b)

        if await self._check_battle_end():
            return

    async def _rotate_queues(self, actor_a: CombatSessionContainerDTO, actor_b: CombatSessionContainerDTO):
        """Возвращает противников в конец очереди, если они живы."""
        if actor_b.state and actor_b.state.hp_current > 0:
            await self.combat_manager.push_to_exchange_queue(self.session_id, actor_a.char_id, actor_b.char_id)

        if actor_a.state and actor_a.state.hp_current > 0:
            await self.combat_manager.push_to_exchange_queue(self.session_id, actor_b.char_id, actor_a.char_id)

    def _apply_thorns_damage(self, actor: CombatSessionContainerDTO, res: dict[str, Any]) -> None:
        if not actor.state:
            return
        thorns_damage = res.get("thorns_damage", 0)
        if thorns_damage > 0:
            actor.state.hp_current = max(0, actor.state.hp_current - thorns_damage)

    def _apply_results(self, actor: CombatSessionContainerDTO, res: dict[str, Any]) -> None:
        if not actor.state:
            return
        actor.state.energy_current = max(0, actor.state.energy_current - res["shield_dmg"])
        actor.state.hp_current = max(0, actor.state.hp_current - res["hp_dmg"])
        if res["hp_dmg"] > 0 and actor.state.hp_current <= 0:
            res["logs"].append("💀 <b>Удар добил противника!</b>")
        for t, c in res.get("tokens_atk", {}).items():
            actor.state.tokens[t] = actor.state.tokens.get(t, 0) + c
        for t, c in res.get("tokens_def", {}).items():
            actor.state.tokens[t] = actor.state.tokens.get(t, 0) + c

    def _apply_regen(self, actor: CombatSessionContainerDTO, stats: dict[str, Any]) -> None:
        if not actor.state or actor.state.hp_current <= 0:
            return

    def _update_stats(self, actor: CombatSessionContainerDTO, out: dict[str, Any], inc: dict[str, Any]) -> None:
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
        self, actor_a: CombatSessionContainerDTO, res_a: dict, actor_b: CombatSessionContainerDTO, res_b: dict
    ) -> None:
        if not actor_a.state or not actor_b.state:
            return
        text_a = CombatLogBuilder.build_log_entry(
            actor_a.name,
            actor_b.name,
            res_a,
            defender_hp=actor_b.state.hp_current,
            defender_energy=actor_b.state.energy_current,
        )
        text_b = CombatLogBuilder.build_log_entry(
            actor_b.name,
            actor_a.name,
            res_b,
            defender_hp=actor_a.state.hp_current,
            defender_energy=actor_a.state.energy_current,
        )
        log_entry = {
            "time": time.time(),
            "round_index": actor_a.state.exchange_count,
            "pair_names": [actor_a.name, actor_b.name],
            "logs": [text_a, text_b],
        }
        await self.combat_manager.push_combat_log(self.session_id, json.dumps(log_entry))

    async def _check_battle_end(self) -> bool:
        p_ids = await self.combat_manager.get_session_participants(self.session_id)
        actors_with_none = {int(pid): await self._get_actor(int(pid)) for pid in p_ids}
        actors = {k: v for k, v in actors_with_none.items() if v is not None}
        winner = VictoryChecker.check_battle_end(actors)
        if winner:
            log.info(f"CombatService | event=battle_ended session_id='{self.session_id}' winner_team='{winner}'")
            await self.lifecycle_service.finish_battle(self.session_id, winner)
            return True
        return False

    async def _get_actor(self, char_id: int) -> CombatSessionContainerDTO | None:
        data = await self.combat_manager.get_rbc_actor_state_json(self.session_id, char_id)
        if not data:
            data = await self.combat_manager.get_actor_json(self.session_id, char_id)
        if data:
            try:
                return CombatSessionContainerDTO.model_validate_json(data)
            except (ValidationError, json.JSONDecodeError) as e:
                log.error(f"Failed to parse actor DTO for {char_id} in session {self.session_id}: {e}")
                return None
        return None

    @staticmethod
    def _get_item_subtype_by_type(actor: CombatSessionContainerDTO, item_type: str) -> str | None:
        for item in actor.equipped_items:
            if item.item_type.value == item_type:
                return item.subtype
        return None

    @staticmethod
    def _determine_xp_outcome(outgoing: dict) -> str:
        if outgoing["is_dodged"]:
            return "miss"
        elif outgoing["is_blocked"]:
            return "partial"
        elif outgoing["is_crit"]:
            return "crit"
        return "success"

    @staticmethod
    def _register_xp_events(actor: CombatSessionContainerDTO, outgoing: dict, incoming: dict) -> None:
        outcome = CombatService._determine_xp_outcome(outgoing)
        CombatXPManager.register_action(actor, "sword", outcome)
        if incoming["damage_total"] > 0:
            armor_subtype = CombatService._get_item_subtype_by_type(actor, "armor")
            if armor_subtype:
                CombatXPManager.register_action(actor, armor_subtype, "success")
        if incoming["is_blocked"]:
            shield_subtype = CombatService._get_item_subtype_by_type(actor, "shield")
            if shield_subtype == "shield" or incoming["block_type"] == "passive":
                CombatXPManager.register_action(actor, "shield", "success")
