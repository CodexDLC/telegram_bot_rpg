from typing import Any

from loguru import logger as log

from apps.game_core.modules.combat.dto import (
    AbilityFlagsDTO,
    ActorSnapshot,
    CombatMoveDTO,
    InteractionResultDTO,
    PipelineContextDTO,
)
from apps.game_core.resources.game_data import GameData
from apps.game_core.resources.game_data.abilities.schemas import (
    AbilityConfigDTO,
    AbilityCostDTO,
)
from apps.game_core.resources.game_data.feints.schemas import (
    FeintConfigDTO,
    FeintCostDTO,
)


class AbilityService:
    """
    Универсальный обработчик способностей (Abilities) и финтов (Feints).
    Отвечает за:
    1. Проверку контроля (Stun/Sleep).
    2. Проверку и списание стоимости (Cost Management).
    3. Применение мутаций перед расчетом (Pre-Calc).
    4. Наложение эффектов после расчета (Post-Calc).
    """

    def pre_process(self, ctx: PipelineContextDTO, move: CombatMoveDTO, actor: ActorSnapshot) -> None:
        """
        Pre-Calc этап.
        """
        # 0. Проверка контроля (Stun/Sleep)
        if self._check_control_effects(actor):
            log.info(f"AbilityService | Actor {actor.char_id} is controlled. Skipping calculation.")
            ctx.phases.run_calculator = False
            ctx.phases.is_interrupted = True
            # TODO: Добавить лог в результат (когда логирование будет готово)
            return

        config = self._get_config(move)
        if not config:
            return

        # 1. Проверка и списание стоимости
        if not self._check_and_pay_cost(actor, config.cost):
            log.info(f"AbilityService | Not enough resources for {config}")
            ctx.phases.run_calculator = False
            ctx.phases.is_interrupted = True
            return

        # 2. Применение инструкций
        self._apply_config_instructions(ctx, config, actor)

    def post_process(
        self,
        ctx: PipelineContextDTO,
        result: InteractionResultDTO,
        source: ActorSnapshot,
        target: ActorSnapshot | None,
        move: CombatMoveDTO,
    ) -> None:
        """
        Post-Calc этап.
        """
        # 1. Обработка флагов от Резолвера (AbilityFlagsDTO)
        self._process_ability_flags(result, source, target)

        # 2. Обработка гарантированных эффектов из конфига
        config = self._get_config(move)
        if config and hasattr(config, "post_calc_effects") and config.post_calc_effects:
            for effect_data in config.post_calc_effects:
                self._apply_effect(source, target, effect_data, result)

    # ==============================================================================
    # INTERNAL LOGIC: CONTROL CHECK
    # ==============================================================================

    def _check_control_effects(self, actor: ActorSnapshot) -> bool:
        """
        Проверяет, находится ли актор под эффектом жесткого контроля (Stun, Sleep).
        """
        for ability in actor.active_abilities:
            # Проверяем payload эффекта
            if ability.payload.get("is_stun") or ability.payload.get("is_sleep"):
                return True
        return False

    # ==============================================================================
    # INTERNAL LOGIC: CONFIG & INSTRUCTIONS
    # ==============================================================================

    def _get_config(self, move: CombatMoveDTO) -> AbilityConfigDTO | FeintConfigDTO | None:
        """Определяет конфигурацию на основе payload хода."""
        if not move or not move.payload:
            return None

        if ability_id := move.payload.get("ability_id"):
            return GameData.get_ability(ability_id)

        if feint_id := move.payload.get("feint_id"):
            return GameData.get_feint(feint_id)

        return None

    def _apply_config_instructions(
        self, ctx: PipelineContextDTO, config: AbilityConfigDTO | FeintConfigDTO, actor: ActorSnapshot
    ) -> None:
        """Применяет мутации и триггеры из конфига."""

        # 1. RAW Mutations (Изменение статов)
        if config.raw_mutations:
            for stat, mutation in config.raw_mutations.items():
                if stat not in actor.raw.modifiers:
                    actor.raw.modifiers[stat] = {"base": 0.0, "source": {}, "temp": {}}

                actor.raw.modifiers[stat]["temp"]["ability"] = mutation
                actor.dirty_stats.add(stat)

        # 2. Pipeline Mutations (Флаги)
        if config.pipeline_mutations:
            for path, value in config.pipeline_mutations.items():
                self._set_nested_flag(ctx.flags, path, value)

        # 3. Triggers (Активация)
        if config.triggers:
            for trigger_name in config.triggers:
                if hasattr(ctx.triggers, trigger_name):
                    setattr(ctx.triggers, trigger_name, True)
                else:
                    log.warning(f"AbilityService | Unknown trigger '{trigger_name}' in config {config}")

        # 4. Override Damage
        if config.override_damage:
            ctx.override_damage = config.override_damage

    def _set_nested_flag(self, flags_obj: Any, path: str, value: Any) -> None:
        """Применяет флаг по пути 'damage.fire' -> flags.damage.fire"""
        parts = path.split(".")
        obj = flags_obj
        try:
            for part in parts[:-1]:
                obj = getattr(obj, part)
            setattr(obj, parts[-1], value)
        except AttributeError:
            log.error(f"AbilityService | Invalid flag path: {path}")

    # ==============================================================================
    # INTERNAL LOGIC: COST MANAGEMENT
    # ==============================================================================

    def _check_and_pay_cost(self, actor: ActorSnapshot, cost: AbilityCostDTO | FeintCostDTO) -> bool:
        """Универсальная проверка и списание стоимости."""

        if isinstance(cost, AbilityCostDTO):
            if not self._can_afford_ability(actor, cost):
                return False
            self._pay_ability(actor, cost)
        elif isinstance(cost, FeintCostDTO):
            if not self._can_afford_feint(actor, cost):
                return False
            self._pay_feint(actor, cost)

        return True

    def _can_afford_ability(self, actor: ActorSnapshot, cost: AbilityCostDTO) -> bool:
        if actor.meta.en < cost.energy:
            return False
        if actor.meta.hp < cost.hp:
            return False
        return not actor.meta.tokens.get("gift", 0) < cost.gift

    def _pay_ability(self, actor: ActorSnapshot, cost: AbilityCostDTO) -> None:
        actor.meta.en -= cost.energy
        actor.meta.hp -= cost.hp
        if cost.gift > 0:
            actor.meta.tokens["gift"] = actor.meta.tokens.get("gift", 0) - cost.gift

    def _can_afford_feint(self, actor: ActorSnapshot, cost: FeintCostDTO) -> bool:
        if cost.tactics:
            for token_type, amount in cost.tactics.items():
                if actor.meta.tokens.get(token_type, 0) < amount:
                    return False
        return True

    def _pay_feint(self, actor: ActorSnapshot, cost: FeintCostDTO) -> None:
        if cost.tactics:
            for token_type, amount in cost.tactics.items():
                actor.meta.tokens[token_type] = actor.meta.tokens.get(token_type, 0) - amount

    # ==============================================================================
    # INTERNAL LOGIC: EFFECTS (POST-CALC)
    # ==============================================================================

    def _process_ability_flags(
        self, result: InteractionResultDTO, source: ActorSnapshot, target: ActorSnapshot | None
    ) -> None:
        """Обрабатывает флаги, выставленные Резолвером."""
        flags: AbilityFlagsDTO = result.ability_flags

        if flags.apply_bleed:
            self._apply_effect(source, target, {"effect_id": "bleed", **flags.pending_effect_data}, result)

        if flags.apply_stun:
            self._apply_effect(source, target, {"effect_id": "stun", **flags.pending_effect_data}, result)

        if flags.grant_counter_marker:
            source.meta.tokens["counter_marker"] = 1

        if flags.grant_evasion_marker:
            source.meta.tokens["evasion_marker"] = 1

    def _apply_effect(
        self,
        source: ActorSnapshot,
        target: ActorSnapshot | None,
        effect_data: dict[str, Any],
        result: InteractionResultDTO,
    ) -> None:
        """
        Накладывает эффект.
        """
        if not target:
            target = source

        effect_id = effect_data.get("effect_id")
        if not effect_id:
            return

        log.info(f"AbilityService | Applying effect '{effect_id}' to {target.char_id}")
