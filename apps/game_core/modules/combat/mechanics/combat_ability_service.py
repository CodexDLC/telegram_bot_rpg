from typing import Any

from loguru import logger as log

from apps.common.schemas_dto import CombatSessionContainerDTO
from apps.game_core.resources.game_data.abilities import ABILITY_LIBRARY
from apps.game_core.resources.game_data.ability_data_struct import (
    AbilityPipelineStep,
    AbilityRules,
)


class AbilityService:
    """
    Сервис для управления и исполнения способностей в бою.

    Отвечает за проверку доступности способностей, списание ресурсов,
    а также интерпретацию и выполнение шагов пайплайна способностей
    (Pre-Calc и Post-Calc фазы).
    """

    @staticmethod
    def get_ability_rules(ability_key: str) -> AbilityRules:
        """
        Возвращает правила (флаги) способности для фазы Pre-Calc.

        Args:
            ability_key: Ключ способности.

        Returns:
            Словарь с правилами способности. Возвращает пустой словарь, если способность не найдена.
        """
        data = ABILITY_LIBRARY.get(ability_key)
        if not data:
            log.warning(f"AbilityService | reason='Ability rules not found' ability_key='{ability_key}'")
            return {}
        return data.get("rules", {})

    @staticmethod
    def can_use_ability(actor: CombatSessionContainerDTO, ability_key: str) -> tuple[bool, str]:
        """
        Проверяет, может ли актор использовать указанную способность.

        Проверяет наличие необходимых ресурсов (энергия, тактика, HP).

        Args:
            actor: DTO актора, пытающегося использовать способность.
            ability_key: Ключ способности для проверки.

        Returns:
            Кортеж `(bool, str)`, где `bool` указывает на возможность использования,
            а `str` содержит сообщение (например, "OK" или причину отказа).
        """
        log.debug(f"AbilityService | action=check_can_use actor_id={actor.char_id} ability_key='{ability_key}'")
        data = ABILITY_LIBRARY.get(ability_key)
        if not data:
            log.warning(
                f"AbilityService | status=failed reason='Ability not found' actor_id={actor.char_id} ability_key='{ability_key}'"
            )
            return False, "Скилл не найден."

        state = actor.state
        if not state:
            log.error(f"AbilityService | status=failed reason='Actor state missing' actor_id={actor.char_id}")
            return False, "Ошибка состояния."

        cost_en = data.get("cost_energy", 0)
        if state.energy_current < cost_en:
            log.info(
                f"AbilityService | status=failed reason='Not enough energy' actor_id={actor.char_id} ability_key='{ability_key}' required={cost_en} actual={state.energy_current}"
            )
            return False, "Не хватает энергии."

        cost_tac = data.get("cost_tactics", 0)
        if state.switch_charges < cost_tac:
            log.info(
                f"AbilityService | status=failed reason='Not enough tactics' actor_id={actor.char_id} ability_key='{ability_key}' required={cost_tac} actual={state.switch_charges}"
            )
            return False, "Не хватает тактики."

        cost_hp = data.get("cost_hp", 0)
        if cost_hp > 0 and state.hp_current <= cost_hp:
            log.info(
                f"AbilityService | status=failed reason='Not enough HP' actor_id={actor.char_id} ability_key='{ability_key}' required={cost_hp} actual={state.hp_current}"
            )
            return False, "Слишком мало здоровья."

        return True, "OK"

    @staticmethod
    def validate_loadout(actor: CombatSessionContainerDTO, abilities_to_check: list[str]) -> tuple[bool, str]:
        """
        Проверяет, достаточно ли ресурсов у актора для использования всего списка способностей.

        Используется для валидации выбора нескольких способностей (например, в UI).

        Args:
            actor: DTO актора.
            abilities_to_check: Список ключей способностей для проверки.

        Returns:
            Кортеж `(bool, str)`, где `bool` указывает на валидность выбора,
            а `str` содержит сообщение (например, "OK" или причину отказа).
        """
        if not actor.state:
            log.error(f"AbilityService | status=failed reason='Actor state missing' actor_id={actor.char_id}")
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
                f"AbilityService | status=failed reason='Not enough energy for loadout' actor_id={actor.char_id} required={total_energy} actual={actor.state.energy_current}"
            )
            return False, f"Не хватает энергии ({total_energy}/{actor.state.energy_current})"

        if actor.state.switch_charges < total_tactics:
            log.info(
                f"AbilityService | status=failed reason='Not enough tactics for loadout' actor_id={actor.char_id} required={total_tactics} actual={actor.state.switch_charges}"
            )
            return False, f"Не хватает тактики ({total_tactics}/{actor.state.switch_charges})"

        if actor.state.hp_current <= total_hp:
            log.info(
                f"AbilityService | status=failed reason='Not enough HP for loadout' actor_id={actor.char_id} required={total_hp} actual={actor.state.hp_current}"
            )
            return False, "Слишком мало здоровья."

        return True, "OK"

    @staticmethod
    def consume_resources(actor: CombatSessionContainerDTO, ability_key: str) -> None:
        """
        Списывает ресурсы актора после успешного применения способности.

        Args:
            actor: DTO актора, использующего способность.
            ability_key: Ключ использованной способности.
        """
        data = ABILITY_LIBRARY.get(ability_key)
        state = actor.state

        if not data or not state:
            log.error(
                f"AbilityService | status=failed reason='Ability data or actor state missing for resource consumption' actor_id={actor.char_id} ability_key='{ability_key}'"
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
            f"AbilityService | event=resources_consumed actor_id={actor.char_id} ability_key='{ability_key}' energy_cost={cost_en} tactics_cost={cost_tac} hp_cost={cost_hp}"
        )

    @staticmethod
    def get_full_pipeline(actor: CombatSessionContainerDTO, active_key: str | None) -> list[AbilityPipelineStep]:
        """
        Собирает полный пайплайн эффектов, включая пассивные и активные способности.

        Args:
            actor: DTO актора, для которого собирается пайплайн.
            active_key: Ключ активной способности, если она используется.

        Returns:
            Список шагов пайплайна, которые будут выполнены.
        """
        pipeline: list[AbilityPipelineStep] = []

        for passive_key in actor.persistent_pipeline:
            data = ABILITY_LIBRARY.get(passive_key)
            if data and "pipeline" in data:
                pipeline.extend(data["pipeline"])

        if active_key:
            data = ABILITY_LIBRARY.get(active_key)
            if data and "pipeline" in data:
                pipeline.extend(data["pipeline"])

        return pipeline

    @staticmethod
    def execute_pre_calc(stats: dict[str, float], flags: dict[str, Any], pipeline: list[AbilityPipelineStep]) -> None:
        """
        Выполняет фазу Pre-Calc пайплайна способностей.

        Модифицирует статы и флаги ДО основного расчета удара.

        Args:
            stats: Словарь агрегированных характеристик актора.
            flags: Словарь флагов, влияющих на расчет.
            pipeline: Список шагов пайплайна.
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
                        f"AbilityService | PreCalcModifyStat stat='{stat_key}' mode='{mode}' value={value} from={original_value} to={stats[stat_key]}"
                    )

            elif action == "set_flag":
                flag_key = params.get("flag")
                val = params.get("value", True)
                if flag_key:
                    flags[flag_key] = val
                    log.trace(f"AbilityService | PreCalcSetFlag flag='{flag_key}' value={val}")

            elif action == "override_damage_type":
                new_type = params.get("type")
                if new_type:
                    flags["override_damage_type"] = new_type
                    log.trace(f"AbilityService | PreCalcOverrideDmgType new_type='{new_type}'")

    @staticmethod
    def execute_post_calc(
        ctx: dict[str, Any],
        actor: CombatSessionContainerDTO,
        target: CombatSessionContainerDTO,
        pipeline: list[AbilityPipelineStep],
    ) -> None:
        """
        Выполняет фазу Post-Calc пайплайна способностей.

        Применяет эффекты (урон, статус, хил) на основе результата удара.

        Args:
            ctx: Контекст расчета удара, содержащий результаты (например, `damage_final`, `is_crit`).
            actor: DTO актора, инициировавшего действие.
            target: DTO целевого актора.
            pipeline: Список шагов пайплайна.
        """
        for step in pipeline:
            if step["phase"] != "post_calc":
                continue

            trigger = step.get("trigger", "always")
            if not AbilityService._check_trigger(trigger, ctx):
                continue

            target_obj = target if step.get("target") == "enemy" else actor
            log.trace(
                f"AbilityService | PostCalcAction trigger='{trigger}' action='{step['action']}' target_id={target_obj.char_id}"
            )
            AbilityService._apply_action(step["action"], step["params"], target_obj, ctx)

    @staticmethod
    def _check_trigger(trigger: str, ctx: dict[str, Any]) -> bool:
        """
        Проверяет условие срабатывания эффекта способности.

        Args:
            trigger: Тип триггера (например, "always", "on_hit", "on_crit").
            ctx: Контекст расчета удара.

        Returns:
            True, если условие триггера выполнено, иначе False.
        """
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
    def _apply_action(
        action: str, params: dict[str, Any], target: CombatSessionContainerDTO, ctx: dict[str, Any]
    ) -> None:
        """
        Применяет конкретное действие способности к целевому актору.

        Args:
            action: Тип действия (например, "deal_damage", "heal", "apply_status").
            params: Параметры действия.
            target: DTO целевого актора.
            ctx: Контекст расчета удара.
        """
        state = target.state
        if not state:
            log.error(
                f"AbilityService | status=failed reason='Target state missing for action' target_id={target.char_id} action='{action}'"
            )
            return

        if action == "deal_damage":
            value = params.get("value", 0)
            if value > 0:
                state.hp_current = max(0, state.hp_current - value)
                dmg_type_str = params.get("type", "true_damage")
                ctx["logs"].append(f"⚡ Дополнительно <b>{value}</b> {dmg_type_str}!")
                log.debug(
                    f"AbilityService | action=deal_damage target_id={target.char_id} damage={value} type='{dmg_type_str}'"
                )

        elif action == "heal":
            value = params.get("value", 0)
            if value > 0:
                from apps.game_core.modules.combat.core.combat_stats_calculator import StatsCalculator

                aggregated_stats = StatsCalculator.aggregate_all(target.stats)
                max_hp = int(aggregated_stats.get("hp_max", state.hp_current))
                state.hp_current = min(max_hp, state.hp_current + value)
                ctx["logs"].append(f"💚 Восстановлено <b>{value}</b> HP.")
                log.debug(f"AbilityService | action=heal target_id={target.char_id} amount={value}")

        elif action == "apply_status":
            status_id = params.get("status_id")
            duration = params.get("duration", 1)
            power = params.get("power", 0)

            if status_id:
                state.effects[status_id] = {"duration": duration, "power": power}
                ctx["logs"].append(f"💀 Наложен эффект: <b>{status_id}</b> ({duration} х.)")
                log.debug(
                    f"AbilityService | action=apply_status target_id={target.char_id} status='{status_id}' duration={duration} power={power}"
                )
