# app/services/game_service/combat/ability_service.py
from typing import Any

from loguru import logger as log

from app.resources.game_data.abilities import ABILITY_LIBRARY
from app.resources.game_data.ability_data_struct import AbilityPipelineStep, AbilityRules
from app.resources.schemas_dto.combat_source_dto import CombatSessionContainerDTO


class AbilityService:
    """
    Сервис-Исполнитель способностей.

    ОТВЕТСТВЕННОСТЬ:
    1. Проверка доступности (Resources, Cooldowns).
    2. Списание ресурсов.
    3. Интерпретация и выполнение шагов пайплайна (Pre/Post calc).
    """

    # =========================================================================
    # 🔍 ПРОВЕРКИ И РЕСУРСЫ
    # =========================================================================

    @staticmethod
    def get_ability_rules(ability_key: str) -> AbilityRules:
        """
        Возвращает флаги правил (Pre-Calc) для калькулятора.

        Args:
            ability_key: Ключ способности.

        Returns:
            Словарь с правилами или пустой словарь.
        """
        data = ABILITY_LIBRARY.get(ability_key)
        if not data:
            log.warning(f"AbilityRulesNotFound | ability_key={ability_key}")
            return {}
        return data.get("rules", {})

    @staticmethod
    def can_use_ability(actor: CombatSessionContainerDTO, ability_key: str) -> tuple[bool, str]:
        """
        Проверяет одиночную способность перед использованием.

        Args:
            actor: DTO актора.
            ability_key: Ключ способности.

        Returns:
            Кортеж (можно ли использовать, причина).
        """
        log.debug(f"CanUseAbilityCheck | actor_id={actor.char_id} ability_key={ability_key}")
        data = ABILITY_LIBRARY.get(ability_key)
        if not data:
            log.warning(
                f"CanUseAbilityFail | reason=ability_not_found actor_id={actor.char_id} ability_key={ability_key}"
            )
            return False, "Скилл не найден."

        state = actor.state
        if not state:
            log.error(f"CanUseAbilityFail | reason=actor_state_missing actor_id={actor.char_id}")
            return False, "Ошибка состояния."

        # 1. Энергия
        cost_en = data.get("cost_energy", 0)
        if state.energy_current < cost_en:
            log.info(
                f"CanUseAbilityFail | reason=no_energy actor_id={actor.char_id} ability_key={ability_key} required={cost_en} actual={state.energy_current}"
            )
            return False, "Не хватает энергии."

        # 2. Тактика
        cost_tac = data.get("cost_tactics", 0)
        if state.switch_charges < cost_tac:
            log.info(
                f"CanUseAbilityFail | reason=no_tactics actor_id={actor.char_id} ability_key={ability_key} required={cost_tac} actual={state.switch_charges}"
            )
            return False, "Не хватает тактики."

        # 3. HP
        cost_hp = data.get("cost_hp", 0)
        if cost_hp > 0 and state.hp_current <= cost_hp:
            log.info(
                f"CanUseAbilityFail | reason=low_hp actor_id={actor.char_id} ability_key={ability_key} required={cost_hp} actual={state.hp_current}"
            )
            return False, "Слишком мало здоровья."

        return True, "OK"

    @staticmethod
    def validate_loadout(actor: CombatSessionContainerDTO, abilities_to_check: list[str]) -> tuple[bool, str]:
        """
        Проверяет, хватит ли ресурсов на ВЕСЬ список способностей сразу.
        (Для UI выбора нескольких скиллов).

        Args:
            actor: DTO актора.
            abilities_to_check: Список ключей способностей.

        Returns:
            Кортеж (валидно ли, причина).
        """
        if not actor.state:
            log.error(f"ValidateLoadoutFail | reason=actor_state_missing actor_id={actor.char_id}")
            return False, "Ошибка состояния."

        total_energy = 0
        total_tactics = 0
        total_hp = 0

        for key in abilities_to_check:
            data = ABILITY_LIBRARY.get(key)
            if not data:
                continue

            total_energy += data.get("cost_energy", 0)
            total_tactics += data.get("cost_tactics", 0)
            total_hp += data.get("cost_hp", 0)

        if actor.state.energy_current < total_energy:
            log.info(
                f"ValidateLoadoutFail | reason=no_energy actor_id={actor.char_id} required={total_energy} actual={actor.state.energy_current}"
            )
            return False, f"Не хватает энергии ({total_energy}/{actor.state.energy_current})"

        if actor.state.switch_charges < total_tactics:
            log.info(
                f"ValidateLoadoutFail | reason=no_tactics actor_id={actor.char_id} required={total_tactics} actual={actor.state.switch_charges}"
            )
            return False, f"Не хватает тактики ({total_tactics}/{actor.state.switch_charges})"

        if actor.state.hp_current <= total_hp:
            log.info(
                f"ValidateLoadoutFail | reason=low_hp actor_id={actor.char_id} required={total_hp} actual={actor.state.hp_current}"
            )
            return False, "Слишком мало здоровья."

        return True, "OK"

    @staticmethod
    def consume_resources(actor: CombatSessionContainerDTO, ability_key: str) -> None:
        """
        Списывает ресурсы после успешного применения.

        Args:
            actor: DTO актора.
            ability_key: Ключ способности.
        """
        data = ABILITY_LIBRARY.get(ability_key)
        state = actor.state

        if not data or not state:
            log.error(
                f"ConsumeResourcesFail | reason=data_or_state_missing actor_id={actor.char_id} ability_key={ability_key}"
            )
            return

        cost_en = data.get("cost_energy", 0)
        if cost_en > 0:
            state.energy_current = max(0, state.energy_current - cost_en)

        cost_tac = data.get("cost_tactics", 0)
        if cost_tac > 0:
            state.switch_charges = max(0, state.switch_charges - cost_tac)

        cost_hp = data.get("cost_hp", 0)
        if cost_hp > 0:
            state.hp_current = max(0, state.hp_current - cost_hp)

        log.info(
            f"ResourcesConsumed | actor_id={actor.char_id} ability_key='{ability_key}' cost_en={cost_en} cost_tac={cost_tac} cost_hp={cost_hp}"
        )

    # =========================================================================
    # ⚙️ ИСПОЛНЕНИЕ ПАЙПЛАЙНА (ENGINE)
    # =========================================================================

    @staticmethod
    def get_full_pipeline(actor: CombatSessionContainerDTO, active_key: str | None) -> list[AbilityPipelineStep]:
        """
        Собирает все эффекты (Пассивные + Активный) в один список.

        Args:
            actor: DTO актора.
            active_key: Ключ активной способности (если есть).

        Returns:
            Список шагов пайплайна.
        """
        pipeline: list[AbilityPipelineStep] = []

        # 1. Пассивные эффекты (от предметов/перков)
        for passive_key in actor.persistent_pipeline:
            data = ABILITY_LIBRARY.get(passive_key)
            if data and "pipeline" in data:
                pipeline.extend(data["pipeline"])

        # 2. Активная способность
        if active_key:
            data = ABILITY_LIBRARY.get(active_key)
            if data and "pipeline" in data:
                pipeline.extend(data["pipeline"])

        return pipeline

    @staticmethod
    def execute_pre_calc(stats: dict[str, float], flags: dict[str, Any], pipeline: list[AbilityPipelineStep]) -> None:
        """
        ФАЗА 1: PRE-CALC.
        Модифицирует статы и флаги ДО расчета удара.
        """
        for step in pipeline:
            if step["phase"] != "pre_calc":
                continue

            action = step["action"]
            params = step["params"]

            if action == "modify_stat":
                stat_key = params.get("stat")
                value = params.get("value", 0.0)
                mode = params.get("mode", "add")

                if stat_key and stat_key in stats:
                    original_value = stats[stat_key]
                    if mode == "add":
                        stats[stat_key] += value
                    elif mode == "mult":
                        stats[stat_key] *= value
                    elif mode == "set":
                        stats[stat_key] = value
                    log.trace(
                        f"PreCalcModifyStat | stat='{stat_key}' mode={mode} value={value} from={original_value} to={stats[stat_key]}"
                    )

            elif action == "set_flag":
                flag_key = params.get("flag")
                val = params.get("value", True)
                if flag_key:
                    flags[flag_key] = val
                    log.trace(f"PreCalcSetFlag | flag='{flag_key}' value={val}")

            elif action == "override_damage_type":
                new_type = params.get("type")
                if new_type:
                    flags["override_damage_type"] = new_type
                    log.trace(f"PreCalcOverrideDmgType | new_type={new_type}")

    @staticmethod
    def execute_post_calc(
        ctx: dict[str, Any],
        actor: CombatSessionContainerDTO,
        target: CombatSessionContainerDTO,
        pipeline: list[AbilityPipelineStep],
    ) -> None:
        """
        ФАЗА 3: POST-CALC.
        Применяет эффекты (урон, статус, хил) на основе результата удара.
        """
        for step in pipeline:
            if step["phase"] != "post_calc":
                continue

            trigger = step.get("trigger", "always")
            if not AbilityService._check_trigger(trigger, ctx):
                continue

            target_obj = target if step.get("target") == "enemy" else actor
            log.trace(f"PostCalcAction | trigger={trigger} action={step['action']} target={target_obj.char_id}")
            AbilityService._apply_action(step["action"], step["params"], target_obj, ctx)

    # --- ХЕЛПЕРЫ ИСПОЛНЕНИЯ ---

    @staticmethod
    def _check_trigger(trigger: str, ctx: dict) -> bool:
        """Проверяет условие срабатывания эффекта."""
        if trigger == "always":
            return True
        if trigger == "on_hit":
            return ctx.get("damage_final", 0) > 0
        if trigger == "on_crit":
            return ctx.get("is_crit", False)
        if trigger == "on_block":
            return ctx.get("is_blocked", False)
        if trigger == "on_dodge":
            return ctx.get("is_dodged", False)
        if trigger == "on_parry":
            return ctx.get("is_parried", False)
        return False

    @staticmethod
    def _apply_action(action: str, params: dict, target: CombatSessionContainerDTO, ctx: dict) -> None:
        """Применяет конкретное изменение к цели."""
        state = target.state
        if not state:
            log.error(f"ApplyActionFail | reason=state_missing target_id={target.char_id} action={action}")
            return

        if action == "deal_damage":
            value = params.get("value", 0)
            if value > 0:
                state.hp_current = max(0, state.hp_current - value)
                dmg_type_str = params.get("type", "true_damage")
                ctx["logs"].append(f"⚡ Дополнительно <b>{value}</b> {dmg_type_str}!")
                log.debug(f"PostCalcDealDamage | target_id={target.char_id} damage={value} type={dmg_type_str}")

        elif action == "heal":
            value = params.get("value", 0)
            if value > 0:
                from app.services.game_service.combat.stats_calculator import StatsCalculator

                aggregated_stats = StatsCalculator.aggregate_all(target.stats)
                max_hp = int(aggregated_stats.get("hp_max", state.hp_current))
                state.hp_current = min(max_hp, state.hp_current + value)
                ctx["logs"].append(f"💚 Восстановлено <b>{value}</b> HP.")
                log.debug(f"PostCalcHeal | target_id={target.char_id} amount={value}")

        elif action == "apply_status":
            status_id = params.get("status_id")
            duration = params.get("duration", 1)
            power = params.get("power", 0)

            if status_id:
                state.effects[status_id] = {"duration": duration, "power": power}
                ctx["logs"].append(f"💀 Наложен эффект: <b>{status_id}</b> ({duration} х.)")
                log.debug(
                    f"PostCalcApplyStatus | target_id={target.char_id} status={status_id} duration={duration} power={power}"
                )
