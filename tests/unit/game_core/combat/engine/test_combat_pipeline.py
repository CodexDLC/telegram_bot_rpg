from unittest.mock import MagicMock, patch

import pytest

from src.backend.domains.user_features.combat.combat_engine.logic.combat_pipeline import CombatPipeline


@pytest.mark.asyncio
@pytest.mark.combat
class TestCombatPipeline:
    @pytest.fixture
    def pipeline(self):
        return CombatPipeline()

    @patch("apps.game_core.modules.combat.combat_engine.logic.combat_pipeline.ContextBuilder")
    @patch("apps.game_core.modules.combat.combat_engine.logic.combat_pipeline.StatsEngine")
    @patch("apps.game_core.modules.combat.combat_engine.logic.combat_pipeline.CombatResolver")
    async def test_pipeline_full_flow(
        self,
        mock_resolver,
        mock_stats_engine,
        mock_builder,
        pipeline,
        basic_actor_snapshot,
        combat_move_attack,
        basic_context,
    ):
        """
        Проверка полного цикла пайплайна.
        """
        # Setup
        mock_builder.build_context.return_value = basic_context

        # Mock AbilityService & MechanicsService inside pipeline instance
        pipeline.ability_service = MagicMock()
        pipeline.mechanics_service = MagicMock()

        # Act
        result = await pipeline.calculate(basic_actor_snapshot, basic_actor_snapshot, combat_move_attack)

        # Assert
        # 1. Context Build
        mock_builder.build_context.assert_called_once()

        # 2. Pre-Calc
        pipeline.ability_service.pre_process.assert_called_once()

        # 3. Stats Engine
        assert mock_stats_engine.ensure_stats.call_count == 2  # Source + Target

        # 4. Resolver
        mock_resolver.resolve_exchange.assert_called_once()

        # 5. Post-Calc
        pipeline.ability_service.post_process.assert_called_once()

        # 6. Mechanics
        pipeline.mechanics_service.apply_interaction_result.assert_called_once()

        assert result == basic_context.result

    @patch("apps.game_core.modules.combat.combat_engine.logic.combat_pipeline.ContextBuilder")
    async def test_pipeline_stop_on_death(
        self, mock_builder, pipeline, basic_actor_snapshot, combat_move_attack, basic_context
    ):
        """
        Проверка остановки пайплайна, если актор мертв.
        """
        mock_builder.build_context.return_value = basic_context

        # Kill source
        basic_actor_snapshot.meta.is_dead = True

        pipeline.ability_service = MagicMock()
        pipeline.mechanics_service = MagicMock()

        # Act
        await pipeline.calculate(basic_actor_snapshot, basic_actor_snapshot, combat_move_attack)

        # Assert
        # Calculator flag should be False
        assert basic_context.phases.run_calculator is False
        assert basic_context.phases.run_post_calc is False

        # Resolver should NOT be called (we can't check static mock here easily without patching class,
        # but we can check flags which control flow)
