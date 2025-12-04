import json
import time
from typing import Any

from loguru import logger as log
from pydantic import ValidationError

from app.resources.schemas_dto.combat_source_dto import CombatSessionContainerDTO
from app.services.core_service.manager.account_manager import AccountManager
from app.services.core_service.manager.combat_manager import CombatManager
from app.services.game_service.combat.ability_service import AbilityService
from app.services.game_service.combat.combat_ai_service import CombatAIService
from app.services.game_service.combat.combat_calculator import CombatCalculator
from app.services.game_service.combat.combat_lifecycle_service import CombatLifecycleService
from app.services.game_service.combat.combat_log_builder import CombatLogBuilder
from app.services.game_service.combat.combat_turn_manager import CombatTurnManager
from app.services.game_service.combat.combat_xp_manager import CombatXPManager
from app.services.game_service.combat.consumable_service import ConsumableService
from app.services.game_service.combat.stats_calculator import StatsCalculator
from app.services.game_service.combat.victory_checker import VictoryChecker


class CombatService:
    """
    Runtime-сервис боя, отвечающий за обработку ходов и расчет результатов.

    Созданием и завершением боя занимается `CombatLifecycleService`.
    """

    def __init__(self, session_id: str, combat_manager: CombatManager, account_manager: AccountManager):
        """
        Инициализирует CombatService.

        Args:
            session_id: Уникальный идентификатор сессии боя.
            combat_manager: Менеджер боя.
            account_manager: Менеджер аккаунтов.
        """
        self.session_id = session_id
        self.combat_manager = combat_manager
        self.account_manager = account_manager
        self.turn_manager = CombatTurnManager(session_id, combat_manager)
        self.lifecycle_service = CombatLifecycleService(combat_manager, account_manager)
        self.ai_service = CombatAIService(combat_manager)
        log.info(f"CombatService | status=initialized session_id='{self.session_id}'")

    async def use_consumable(self, actor_id: int, item_id: int) -> tuple[bool, str]:
        """
        Использует расходуемый предмет в бою.

        Args:
            actor_id: ID актора, использующего предмет.
            item_id: ID предмета.

        Returns:
            Кортеж (успех, сообщение).
        """
        actor = await self._get_actor(actor_id)
        if not actor:
            return False, "Ошибка данных актора."

        success, msg = ConsumableService.use_item(actor, item_id)

        if success:
            await self.combat_manager.save_actor_json(self.session_id, actor_id, actor.model_dump_json())

        return success, msg

    async def switch_target(self, actor_id: int, new_target_id: int) -> tuple[bool, str]:
        """
        Изменяет текущую цель для атакующего актора во время боя.

        Args:
            actor_id: Идентификатор актора, меняющего цель.
            new_target_id: Идентификатор новой цели.

        Returns:
            Кортеж `(bool, str)`, где `bool` указывает на успешность операции,
            а `str` содержит соответствующее сообщение.
        """
        log.info(
            f"CombatService | action=switch_target actor_id={actor_id} new_target_id={new_target_id} session_id='{self.session_id}'"
        )
        actor = await self._get_actor(actor_id)
        if not actor or not actor.state:
            log.warning(
                f"CombatService | status=failed reason='Actor data missing' actor_id={actor_id} session_id='{self.session_id}'"
            )
            return False, "Ошибка данных."

        if not actor.state.targets or new_target_id not in actor.state.targets:
            log.warning(
                f"CombatService | status=failed reason='Invalid target' actor_id={actor_id} new_target_id={new_target_id} session_id='{self.session_id}'"
            )
            return False, "Недопустимая цель."

        if actor.state.targets[0] == new_target_id:
            log.warning(
                f"CombatService | status=failed reason='Target already selected' actor_id={actor_id} new_target_id={new_target_id} session_id='{self.session_id}'"
            )
            return False, "Эта цель уже выбрана."

        if actor.state.switch_charges <= 0:
            log.warning(
                f"CombatService | status=failed reason='No switch charges' actor_id={actor_id} session_id='{self.session_id}'"
            )
            return False, "Не хватает очков тактики."

        actor.state.switch_charges -= 1

        try:
            idx = actor.state.targets.index(new_target_id)
            actor.state.targets[0], actor.state.targets[idx] = (actor.state.targets[idx], actor.state.targets[0])
        except ValueError:
            log.exception(
                f"CombatService | status=failed reason='Target list manipulation error' actor_id={actor_id} new_target_id={new_target_id} targets={actor.state.targets}"
            )
            return False, "Ошибка списка."

        await self.combat_manager.save_actor_json(self.session_id, actor_id, actor.model_dump_json())
        log.info(
            f"CombatService | action=switch_target status=success actor_id={actor_id} new_target_id={new_target_id} charges_left={actor.state.switch_charges}"
        )
        return True, f"Цель изменена. Осталось смен: {actor.state.switch_charges}"

    async def register_move(
        self,
        actor_id: int,
        target_id: int | None,
        attack_zones: list[str] | None,
        block_zones: list[str] | None,
        ability_key: str | None = None,
    ) -> None:
        """
        Регистрирует ход актора и запускает расчет обмена, если оба хода сделаны.

        Args:
            actor_id: Идентификатор актора, совершающего ход.
            target_id: Идентификатор цели хода. Если None, используется текущая цель актора.
            attack_zones: Список зон атаки.
            block_zones: Список зон блокировки.
            ability_key: Ключ используемой способности.
        """
        log.debug(
            f"CombatService | action=register_move actor_id={actor_id} target_id={target_id} session_id='{self.session_id}'"
        )
        actor = await self._get_actor(actor_id)
        if not actor or not actor.state:
            log.warning(
                f"CombatService | status=failed reason='Actor data missing' actor_id={actor_id} session_id='{self.session_id}'"
            )
            return

        real_target_id = target_id
        if real_target_id is None:
            if actor.state.targets:
                real_target_id = actor.state.targets[0]
            else:
                log.warning(
                    f"CombatService | status=failed reason='No target available' actor_id={actor_id} session_id='{self.session_id}'"
                )
                return

        exchange_data = await self.turn_manager.register_move_request(
            actor_id, real_target_id, attack_zones, block_zones, ability_key
        )

        if exchange_data:
            log.info(
                f"CombatService | event=exchange_pair_ready actor_a={actor_id} actor_b={real_target_id} session_id='{self.session_id}'"
            )
            await self._process_exchange(
                actor_id, exchange_data["my_move"], real_target_id, exchange_data["enemy_move"]
            )
            await self._process_ai_turns()
            await self.check_deadlines()
        else:
            target_actor = await self._get_actor(real_target_id)
            if target_actor and target_actor.is_ai:
                log.debug(
                    f"CombatService | event=ai_turn_check ai_actor_id={real_target_id} session_id='{self.session_id}'"
                )
                decision = await self.ai_service.calculate_action(target_actor, self.session_id)
                if decision:
                    await self._process_ai_turns()

    async def check_deadlines(self) -> None:
        """
        Проверяет и обрабатывает истекшие таймеры ходов для участников боя.
        """
        participants = await self.combat_manager.get_session_participants(self.session_id)
        actors_map: dict[int, CombatSessionContainerDTO] = {}
        for pid in participants:
            actor = await self._get_actor(int(pid))
            if actor:
                actors_map[int(pid)] = actor

        expired_list = await self.turn_manager.check_expired_deadlines(actors_map)

        for lazy_id, agg_id in expired_list:
            log.warning(
                f"CombatService | event=deadline_expired lazy_actor_id={lazy_id} opponent_id={agg_id} session_id='{self.session_id}'"
            )
            await self.register_move(
                actor_id=lazy_id, target_id=agg_id, attack_zones=None, block_zones=None, ability_key=None
            )

    async def _process_ai_turns(self) -> None:
        """
        Обрабатывает ходы всех AI-участников в текущей боевой сессии.
        """
        participants = await self.combat_manager.get_session_participants(self.session_id)
        for pid_str in participants:
            pid = int(pid_str)
            actor = await self._get_actor(pid)

            if not actor or not actor.is_ai or (actor.state and actor.state.hp_current <= 0):
                continue

            decision = await self.ai_service.calculate_action(actor, self.session_id)
            if not decision:
                continue

            target_id = decision.get("target_id")
            if not target_id:
                continue

            existing = await self.combat_manager.get_pending_move(self.session_id, pid, target_id)
            if existing:
                continue

            log.info(
                f"CombatService | event=ai_making_move actor_id={pid} target_id={target_id} session_id='{self.session_id}'"
            )
            await self.register_move(
                actor_id=pid,
                target_id=target_id,
                attack_zones=decision["attack"],
                block_zones=decision["block"],
                ability_key=decision.get("ability"),
            )

    async def _process_exchange(self, id_a: int, move_a: dict, id_b: int, move_b: dict) -> None:
        """
        Обрабатывает обмен ходами между двумя акторами.

        Args:
            id_a: Идентификатор первого актора.
            move_a: Данные хода первого актора.
            id_b: Идентификатор второго актора.
            move_b: Данные хода второго актора.
        """
        log.debug(
            f"CombatService | action=process_exchange actor_a={id_a} actor_b={id_b} session_id='{self.session_id}'"
        )
        actor_a = await self._get_actor(id_a)
        actor_b = await self._get_actor(id_b)

        if not actor_a or not actor_b or not actor_a.state or not actor_b.state:
            log.error(
                f"CombatService | status=failed reason='Actor data missing for exchange' a_id={id_a} b_id={id_b} session_id='{self.session_id}'"
            )
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

        await self.combat_manager.save_actor_json(self.session_id, id_a, actor_a.model_dump_json())
        await self.combat_manager.save_actor_json(self.session_id, id_b, actor_b.model_dump_json())
        await self._log_exchange(actor_a, res_a, actor_b, res_b)

        if await self._check_battle_end():
            return

    def _apply_thorns_damage(self, actor: CombatSessionContainerDTO, res: dict[str, Any]) -> None:
        """
        Применяет отраженный урон (thorns damage) к актору.

        Args:
            actor: DTO актора, получающего урон.
            res: Результаты расчета удара, содержащие `thorns_damage`.
        """
        if not actor.state:
            return

        thorns_damage = res.get("thorns_damage", 0)
        if thorns_damage > 0:
            actor.state.hp_current = max(0, actor.state.hp_current - thorns_damage)
            log.debug(f"CombatService | action=thorns_damage_applied char_id={actor.char_id} damage={thorns_damage}")

    def _apply_results(self, actor: CombatSessionContainerDTO, res: dict[str, Any]) -> None:
        """
        Применяет результаты удара к актору (урон по HP/Energy, токены).

        Args:
            actor: DTO актора, к которому применяются результаты.
            res: Результаты расчета удара.
        """
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
        """
        Применяет регенерацию HP и Energy к актору.

        Args:
            actor: DTO актора, к которому применяется регенерация.
            stats: Агрегированные статы актора, содержащие `hp_max`, `energy_max`, `hp_regen`, `energy_regen`.
        """
        if not actor.state or actor.state.hp_current <= 0:
            return
        max_hp = int(stats.get("hp_max", 1.0))
        max_en = int(stats.get("energy_max", 0.0))
        actor.state.hp_current = min(max_hp, actor.state.hp_current + int(stats.get("hp_regen", 0.0)))
        actor.state.energy_current = min(max_en, actor.state.energy_current + int(stats.get("energy_regen", 0.0)))

    def _update_stats(self, actor: CombatSessionContainerDTO, out: dict[str, Any], inc: dict[str, Any]) -> None:
        """
        Обновляет боевую статистику актора (нанесенный/полученный урон, криты, блоки, увороты).

        Args:
            actor: DTO актора, чья статистика обновляется.
            out: Результаты исходящего удара.
            inc: Результаты входящего удара.
        """
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
        res_a: dict[str, Any],
        actor_b: CombatSessionContainerDTO,
        res_b: dict[str, Any],
    ) -> None:
        """
        Формирует и сохраняет запись об обмене ходами в лог боя.

        Args:
            actor_a: DTO первого актора.
            res_a: Результаты удара первого актора.
            actor_b: DTO второго актора.
            res_b: Результаты удара второго актора.
        """
        if not actor_a.state or not actor_b.state:
            return

        combined_logs = []
        # Лог для actor_a, атакующего actor_b
        text_a = CombatLogBuilder.build_log_entry(
            f"⚔️ {actor_a.name}",  # Атакующий с эмодзи
            f"🛡️ {actor_b.name}",  # Защищающийся с эмодзи
            res_a,
            defender_hp=actor_b.state.hp_current,
            defender_energy=actor_b.state.energy_current,
        )
        combined_logs.append(text_a)

        # Лог для actor_b, атакующего actor_a
        text_b = CombatLogBuilder.build_log_entry(
            f"⚔️ {actor_b.name}",  # Атакующий с эмодзи
            f"🛡️ {actor_a.name}",  # Защищающийся с эмодзи
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
        await self.combat_manager.push_combat_log(self.session_id, json.dumps(log_entry))
        log.debug(
            f"CombatService | event=exchange_logged session_id='{self.session_id}' round={actor_a.state.exchange_count}"
        )

    async def _check_battle_end(self) -> bool:
        """
        Проверяет, завершился ли бой.

        Returns:
            True, если бой завершен, иначе False.
        """
        p_ids = await self.combat_manager.get_session_participants(self.session_id)
        actors: dict[int, CombatSessionContainerDTO] = {}
        for pid in p_ids:
            actor = await self._get_actor(int(pid))
            if actor:
                actors[int(pid)] = actor

        winner = VictoryChecker.check_battle_end(actors)
        if winner:
            log.info(f"CombatService | event=battle_ended session_id='{self.session_id}' winner_team='{winner}'")
            await self.lifecycle_service.finish_battle(self.session_id, winner)
            return True
        return False

    async def process_turn_updates(self) -> None:
        """
        Обрабатывает все необходимые обновления боя, включая ходы AI и проверку дедлайнов.

        Этот метод является публичной оберткой для вызова из хэндлеров.
        """
        log.debug(f"CombatService | action=process_turn_updates session_id='{self.session_id}'")
        await self._process_ai_turns()
        await self.check_deadlines()

    async def _get_actor(self, char_id: int) -> CombatSessionContainerDTO | None:
        """
        Получает DTO актора из Redis.

        Args:
            char_id: Идентификатор актора.

        Returns:
            DTO актора, если найден и успешно десериализован, иначе None.
        """
        data = await self.combat_manager.get_actor_json(self.session_id, char_id)
        if data:
            try:
                return CombatSessionContainerDTO.model_validate_json(data)
            except json.JSONDecodeError:
                log.exception(
                    f"CombatService | status=failed reason='JSON decode error for actor' char_id={char_id} session_id='{self.session_id}' data='{data}'"
                )
                return None
            except ValidationError:
                log.exception(
                    f"CombatService | status=failed reason='Pydantic validation error for actor' char_id={char_id} session_id='{self.session_id}' data='{data}'"
                )
                return None
        log.warning(
            f"CombatService | status=failed reason='Actor not found' char_id={char_id} session_id='{self.session_id}'"
        )
        return None

    @staticmethod
    def _get_item_subtype_by_type(actor: CombatSessionContainerDTO, item_type: str) -> str | None:
        """
        Ищет экипированный предмет определенного типа и возвращает его подтип.

        Args:
            actor: DTO актора, чьи экипированные предметы проверяются.
            item_type: Тип предмета для поиска (например, "weapon", "armor").

        Returns:
            Подтип предмета, если найден, иначе None.
        """
        for item in actor.equipped_items:
            if item.item_type.value == item_type:
                return item.subtype
        return None

    @staticmethod
    def _determine_xp_outcome(outgoing: dict[str, Any]) -> str:
        """
        Определяет исход действия для регистрации опыта.

        Args:
            outgoing: Результаты исходящего удара.

        Returns:
            Строка, описывающая исход ("miss", "partial", "crit", "success").
        """
        if outgoing["is_dodged"]:
            return "miss"
        elif outgoing["is_blocked"]:
            return "partial"
        elif outgoing["is_crit"]:
            return "crit"
        return "success"

    @staticmethod
    def _register_xp_events(
        actor: CombatSessionContainerDTO, outgoing: dict[str, Any], incoming: dict[str, Any]
    ) -> None:
        """
        Регистрирует события опыта за действия в раунде, учитывая экипировку.

        Args:
            actor: DTO актора, для которого регистрируется опыт.
            outgoing: Результаты исходящего удара.
            incoming: Результаты входящего удара.
        """
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
