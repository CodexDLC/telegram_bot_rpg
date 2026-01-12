from typing import Any

from apps.game_core.modules.combat.services.ability_service import AbilityService
from apps.game_core.modules.combat.services.mechanics_service import MechanicsService

from apps.common.schemas_dto.combat_source_dto import CombatMoveDTO
from apps.game_core.modules.combat.combat_engine.logic.combat_resolver import CombatResolver
from apps.game_core.modules.combat.combat_engine.logic.context_builder import ContextBuilder
from apps.game_core.modules.combat.combat_engine.logic.stats_engine import StatsEngine
from apps.game_core.modules.combat.dto.combat_internal_dto import ActorSnapshot, InteractionResultDTO


class CombatPipeline:
    """
    Оркестратор боевого взаимодействия (Combat Pipeline).
    Выполняет полный цикл обработки одного удара/действия.
    """

    def __init__(self):
        self.ability_service = AbilityService()
        self.mechanics_service = MechanicsService()
        # Resolver и ContextBuilder - статические/без состояния

    async def calculate(
        self,
        source: ActorSnapshot,
        target: ActorSnapshot | None,
        move: CombatMoveDTO,
        external_mods: dict[str, Any] | None = None,
    ) -> InteractionResultDTO:
        """
        Запуск пайплайна (Async).
        """
        # 0. Context Build
        ctx = ContextBuilder.build_context(source, target, move, external_mods)

        # 1. Pre-Calculation (Ability Service)
        if ctx.phases.run_pre_calc:
            self.ability_service.pre_process(ctx, move)

        # 1.5. Stats Calculation (Stats Engine)
        # Актуализируем статы (если были изменения в pre-calc)
        StatsEngine.ensure_stats(source)
        if target:
            StatsEngine.ensure_stats(target)

        # 1.6. Liveness Check
        if not source.is_alive:
            return InteractionResultDTO(logs=["Attacker is dead"])
        if target and not target.is_alive:
            return InteractionResultDTO(logs=["Target is dead"])

        # 2. Calculator (Resolver)
        result = InteractionResultDTO()
        if ctx.phases.run_calculator and target and source.stats and target.stats:
            result = CombatResolver.resolve_exchange(source.stats, target.stats, ctx)

        # 3. Post-Calculation (Ability Service)
        if ctx.phases.run_post_calc:
            self.ability_service.post_process(ctx, result)

        # 4. Mechanics (Apply Results)
        self.mechanics_service.apply_interaction_result(ctx, result)

        return result
