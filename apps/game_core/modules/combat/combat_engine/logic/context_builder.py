from typing import Any

from loguru import logger as log

from apps.game_core.modules.combat.combat_engine.logic.math_core import MathCore
from apps.game_core.modules.combat.dto import (
    ActorSnapshot,
    CombatMoveDTO,
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
        # Убрано: проверка контроля перенесена в AbilityService.pre_process

        # 2. Dual Wield Check (Только если атака не отключена)
        if not mods_a.get("disable_attack") and ContextBuilder._check_dual_wield(source):
            mods_a["trigger_dual_wield"] = True
            log.info(f"ContextBuilder | Actor {source.char_id} triggered Dual Wield")

        if move_b and not mods_b.get("disable_attack") and ContextBuilder._check_dual_wield(target):
            mods_b["trigger_dual_wield"] = True
            log.info(f"ContextBuilder | Actor {target.char_id} triggered Dual Wield")

        return mods_a, mods_b

    @staticmethod
    def _check_dual_wield(actor: ActorSnapshot) -> bool:
        """Проверяет возможность и шанс удара второй рукой."""
        off_hand_skill = actor.loadout.layout.get("off_hand")
        if not off_hand_skill or "shield" in off_hand_skill:
            return False

        skill_val = actor.skills.get("skill_dual_wield", 0.0)
        chance = 0.25 + (skill_val * 0.01)

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
        НЕ сохраняет actor/target в DTO, только настраивает флаги.
        """
        # 1. Базовая инициализация (Чистый DTO)
        ctx = PipelineContextDTO(
            phases=PipelinePhasesDTO(),
            flags=PipelineFlagsDTO(),
            mods=PipelineModsDTO(),
            stages=PipelineStagesDTO(),
            triggers=PipelineTriggersDTO(),
        )

        # 2. Применение внешних модификаторов (Interference)
        if external_mods:
            ContextBuilder._apply_external_mods(ctx, external_mods)

        # 3. Анализ Интента (Move Analysis) - Атакующий
        ContextBuilder._analyze_intent(ctx, actor, move, external_mods)

        # 4. Анализ Защиты (Defense Analysis) - Защитник
        if target:
            ContextBuilder._analyze_defense(ctx, target)

        return ctx

    @staticmethod
    def _apply_external_mods(ctx: PipelineContextDTO, mods: dict[str, Any]) -> None:
        """
        Применяет модификаторы от InterferenceService.
        """
        if mods.get("disable_attack"):
            ctx.phases.run_calculator = False

    @staticmethod
    def _analyze_intent(
        ctx: PipelineContextDTO, actor: ActorSnapshot, move: CombatMoveDTO, external_mods: dict[str, Any] | None
    ) -> None:
        """
        Настраивает мета-флаги Атаки (Source Type, Weapon Class).
        """
        strategy = move.strategy

        # 1. MAGIC / SKILL
        if strategy == "instant":
            ctx.flags.meta.source_type = "magic"
            return

        # 2. ITEM
        if strategy == "item":
            ctx.flags.meta.source_type = "item"
            return

        # 3. EXCHANGE (Melee/Ranged Attack)
        # Определяем Source Type (main_hand / off_hand)
        source_type = "main_hand"
        if external_mods and "source_type" in external_mods:
            source_type = external_mods["source_type"]

        ctx.flags.meta.source_type = source_type

        # Определяем Weapon Class (для скиллов и триггеров)
        if source_type in ["main_hand", "off_hand"]:
            weapon_skill_key = actor.loadout.layout.get(source_type)
            # Пример: "skill_swords" -> "swords"
            if weapon_skill_key and weapon_skill_key.startswith("skill_"):
                ctx.flags.meta.weapon_class = weapon_skill_key.replace("skill_", "")

    @staticmethod
    def _analyze_defense(ctx: PipelineContextDTO, target: ActorSnapshot) -> None:
        """
        Настраивает флаги Защиты (Armor Type, Shield).
        """
        layout = target.loadout.layout

        # 1. Armor Type (Body)
        body_skill = layout.get("body")
        if body_skill == "skill_light_armor":
            ctx.flags.mastery.light_armor = True
        elif body_skill == "skill_medium_armor":
            ctx.flags.mastery.medium_armor = True

        # 2. Shield (Off-hand)
        off_hand_skill = layout.get("off_hand")
        if off_hand_skill == "skill_shield":
            ctx.flags.mastery.shield_reflect = True
