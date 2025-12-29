import json
import time
from typing import Any

from loguru import logger as log
from pydantic import ValidationError

from apps.common.schemas_dto import CombatSessionContainerDTO
from apps.common.services.core_service import CombatManager
from apps.common.services.core_service.manager.account_manager import AccountManager
from apps.game_core.modules.combat.core.combat_calculator import CombatCalculator
from apps.game_core.modules.combat.core.combat_log_builder import CombatLogBuilder
from apps.game_core.modules.combat.core.combat_stats_calculator import StatsCalculator
from apps.game_core.modules.combat.core.combat_xp_manager import CombatXPManager
from apps.game_core.modules.combat.mechanics.combat_ability_service import AbilityService
from apps.game_core.modules.combat.mechanics.combat_consumable_service import ConsumableService
from apps.game_core.modules.combat.session.initialization.combat_lifecycle_service import CombatLifecycleService


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

        # Используем правильные ключи из CombatMoveDTO
        attack_a = move_a.get("attack_zones", [])
        block_b = move_b.get("block_zones", [])
        attack_b = move_b.get("attack_zones", [])
        block_a = move_a.get("block_zones", [])

        res_a = CombatCalculator.calculate_hit(
            stats_a, stats_b, actor_b.state.energy_current, attack_a, block_b, flags=flags_a
        )
        res_b = CombatCalculator.calculate_hit(
            stats_b, stats_a, actor_a.state.energy_current, attack_b, block_a, flags=flags_b
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

        # --- ЛОГИКА СМЕРТИ И ПОБЕДЫ ---
        # Проверяем, умер ли кто-то в этом раунде
        new_dead_ids = []
        if actor_a.state.hp_current <= 0:
            new_dead_ids.append(actor_a.char_id)
        if actor_b.state.hp_current <= 0:
            new_dead_ids.append(actor_b.char_id)

        # Если есть жертвы, запускаем процедуру обновления меты и проверки победы
        if new_dead_ids:
            await self._handle_casualties(new_dead_ids)

    async def _handle_casualties(self, new_dead_ids: list[int]):
        """
        Обрабатывает смерти: обновляет список dead_actors в мете и проверяет условие победы.
        """
        # 1. Читаем мету (Single Source of Truth)
        meta = await self.combat_manager.get_rbc_session_meta(self.session_id)
        if not meta:
            return

        try:
            teams = json.loads(meta.get("teams", "{}"))
            # Получаем текущий список мертвых и добавляем новых
            dead_actors = set(json.loads(meta.get("dead_actors", "[]")))
            dead_actors.update(new_dead_ids)
        except json.JSONDecodeError:
            log.error(f"CombatService | Meta parse error session_id='{self.session_id}'")
            return

        # 2. Проверяем условие победы
        alive_teams = []
        for team_name, members in teams.items():
            # Команда жива, если хотя бы один участник НЕ в списке мертвых
            if any(m for m in members if m not in dead_actors):
                alive_teams.append(team_name)

        # 3. Принимаем решение
        if len(alive_teams) <= 1:
            # ПОБЕДА: Завершаем бой (ставит active=0)
            winner = alive_teams[0] if alive_teams else "draw"
            log.info(f"CombatService | Victory! session_id='{self.session_id}' winner='{winner}' dead={new_dead_ids}")

            # Важно: Сначала обновляем список мертвых в мете, чтобы finish_battle мог (если нужно) его использовать,
            # или просто для консистентности перед закрытием.
            # Но finish_battle перезапишет мету. Поэтому передаем управление туда.
            # Однако, чтобы в истории остались правильные dead_actors, лучше обновить их сейчас.
            # Но так как finish_battle делает active=0, это главное.

            # Обновляем dead_actors перед финишем (опционально, но полезно для UI/логов)
            await self.combat_manager.create_rbc_session_meta(
                self.session_id, {"dead_actors": json.dumps(list(dead_actors))}
            )

            await self.lifecycle_service.finish_battle(self.session_id, winner)
        else:
            # БОЙ ПРОДОЛЖАЕТСЯ: Просто обновляем список трупов
            log.info(f"CombatService | Casualty update session_id='{self.session_id}' new_dead={new_dead_ids}")
            await self.combat_manager.create_rbc_session_meta(
                self.session_id, {"dead_actors": json.dumps(list(dead_actors))}
            )

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

    async def _get_actor(self, char_id: int) -> CombatSessionContainerDTO | None:
        # Убрали fallback на старый get_actor_json
        data = await self.combat_manager.get_rbc_actor_state_json(self.session_id, char_id)
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

        # 1. Оружие (или кулаки)
        # Пытаемся найти оружие в экипировке
        weapon_subtype = None
        for item in actor.equipped_items:
            if item.item_type.value == "weapon":
                weapon_subtype = item.subtype
                break

        # Если оружия нет - считаем как "unarmed"
        if not weapon_subtype:
            weapon_subtype = "unarmed"

        CombatXPManager.register_action(actor, weapon_subtype, outcome)

        # 2. Броня (при получении урона)
        if incoming["damage_total"] > 0:
            armor_subtype = CombatService._get_item_subtype_by_type(actor, "armor")
            if armor_subtype:
                CombatXPManager.register_action(actor, armor_subtype, "success")

        # 3. Щит (при блоке)
        if incoming["is_blocked"]:
            shield_subtype = CombatService._get_item_subtype_by_type(actor, "shield")
            if shield_subtype == "shield" or incoming["block_type"] == "passive":
                CombatXPManager.register_action(actor, "shield", "success")
