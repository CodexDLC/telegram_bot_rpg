from typing import Any

from loguru import logger as log

from apps.common.schemas_dto.combat_source_dto import CombatMoveDTO
from apps.game_core.modules.combat.combat_engine.logic.math_core import MathCore
from apps.game_core.modules.combat.dto.combat_internal_dto import ActorSnapshot
from apps.game_core.modules.combat.dto.combat_pipeline_dto import (
    PipelineContextDTO,
    PipelineFlagsDTO,
    PipelineModsDTO,
    PipelinePhasesDTO,
    PipelineStagesDTO,
    PipelineTriggersDTO,
)


class ContextBuilder:
    """
    Фабрика контекста боя (Context Builder).
    Создает 'пульт управления' (PipelineContextDTO) для конкретного взаимодействия.
    """

    @staticmethod
    def analyze_exchange(
        source: ActorSnapshot,
        target: ActorSnapshot,
        move_a: CombatMoveDTO,
        move_b: CombatMoveDTO | None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """
        Анализирует намерения участников ДО создания задач.
        Проверяет Interference (стан) и Dual Wield.
        Возвращает (mods_a, mods_b).
        """
        mods_a: dict[str, Any] = {}
        mods_b: dict[str, Any] = {}

        # 1. Interference Check (Stun/Sleep)
        # Проверяем source
        if ContextBuilder._check_control_effects(source):
            mods_a["disable_attack"] = True
            log.info(f"ContextBuilder | Actor {source.char_id} is controlled (stun/sleep)")

        # Проверяем target (если он тоже атакует в ответ)
        if move_b and ContextBuilder._check_control_effects(target):
            mods_b["disable_attack"] = True
            log.info(f"ContextBuilder | Actor {target.char_id} is controlled (stun/sleep)")

        # 2. Dual Wield Check (Только если атака не отключена)
        if not mods_a.get("disable_attack") and ContextBuilder._check_dual_wield(source):
            mods_a["trigger_dual_wield"] = True
            log.info(f"ContextBuilder | Actor {source.char_id} triggered Dual Wield")

        if move_b and not mods_b.get("disable_attack") and ContextBuilder._check_dual_wield(target):
            mods_b["trigger_dual_wield"] = True
            log.info(f"ContextBuilder | Actor {target.char_id} triggered Dual Wield")

        return mods_a, mods_b

    @staticmethod
    def _check_control_effects(actor: ActorSnapshot) -> bool:
        """Проверяет наличие эффектов контроля."""
        for ability in actor.active_abilities:
            # TODO: Проверять теги эффекта (is_stun, is_sleep)
            # Пока заглушка: смотрим payload
            if ability.payload.get("is_stun") or ability.payload.get("is_sleep"):
                return True
        return False

    @staticmethod
    def _check_dual_wield(actor: ActorSnapshot) -> bool:
        """Проверяет возможность и шанс удара второй рукой."""
        # 1. Проверяем наличие оружия в off_hand
        off_hand_skill = actor.loadout.layout.get("off_hand")
        if not off_hand_skill or "shield" in off_hand_skill:
            return False

        # 2. Проверяем шанс (Skill Dual Wield)
        # Шанс = 25% (база) + бонусы?
        # Берем уровень скилла из snapshot.skills (если есть)
        skill_val = actor.skills.get("skill_dual_wield", 0.0)
        chance = 0.25 + (skill_val * 0.01)  # Пример формулы

        return MathCore.check_chance(chance)

    @staticmethod
    def build_context(
        actor: ActorSnapshot,
        target: ActorSnapshot | None,
        move: CombatMoveDTO,
        external_mods: dict[str, Any] | None = None,
    ) -> PipelineContextDTO:
        """
        Сборка контекста.
        """
        # 1. Базовая инициализация
        ctx = PipelineContextDTO(
            actor=actor,
            target=target,
            phases=PipelinePhasesDTO(),
            flags=PipelineFlagsDTO(),
            mods=PipelineModsDTO(),
            stages=PipelineStagesDTO(),
            triggers=PipelineTriggersDTO(),
        )

        # 2. Применение внешних модификаторов (Interference)
        if external_mods:
            ContextBuilder._apply_external_mods(ctx, external_mods)

        # 3. Анализ Интента (Move Analysis)
        ContextBuilder._analyze_intent(ctx, move, external_mods)

        return ctx

    @staticmethod
    def _apply_external_mods(ctx: PipelineContextDTO, mods: dict[str, Any]) -> None:
        """
        Применяет модификаторы от InterferenceService (прерывание, оглушение).
        """
        if mods.get("disable_attack"):
            ctx.phases.run_calculator = False
            # Но оставляем run_post_calc, чтобы снять дебаффы или триггернуть "Fail"

    @staticmethod
    def _analyze_intent(ctx: PipelineContextDTO, move: CombatMoveDTO, external_mods: dict[str, Any] | None) -> None:
        """
        Настраивает флаги на основе типа атаки (Skill, Item, Basic).
        """
        payload = move.payload

        # Определяем тип источника (main_hand, off_hand, magic)
        # По умолчанию - main_hand, если не переопределено в external_mods
        source_type = "main_hand"
        if external_mods and "source_type" in external_mods:
            source_type = external_mods["source_type"]

        ctx.flags.meta.source_type = source_type

        # Если это скилл - смотрим его свойства (пока заглушка)
        skill_id = payload.get("skill_id")
        if skill_id:
            # TODO: Load skill config and set flags
            # if skill.is_magic: ctx.flags.damage.fire = True
            pass

        # Если это предмет
        item_id = payload.get("item_id")
        if item_id:
            # TODO: Load item config
            pass
