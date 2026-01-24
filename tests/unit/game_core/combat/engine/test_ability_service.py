from unittest.mock import MagicMock, patch

import pytest

from backend.domains.user_features.combat.combat_engine.logic.ability_service import AbilityService
from backend.resources.game_data.abilities.schemas import AbilityConfigDTO, AbilityCostDTO
from backend.resources.game_data.effects.schemas import EffectDTO, EffectType


@pytest.mark.combat
class TestAbilityService:
    @pytest.fixture
    def service(self):
        return AbilityService()

    @patch("apps.game_core.modules.combat.combat_engine.logic.ability_service.GameData")
    def test_pre_process_cost_check_success(
        self, mock_game_data, service, basic_context, combat_move_attack, basic_actor_snapshot
    ):
        """
        Проверка списания стоимости (успех).
        """
        # Setup
        combat_move_attack.payload = MagicMock()
        combat_move_attack.payload.ability_id = "test_ability"

        config = AbilityConfigDTO(
            ability_id="test_ability", name_ru="Test", description_ru="Desc", cost=AbilityCostDTO(energy=10)
        )
        mock_game_data.get_ability.return_value = config

        basic_actor_snapshot.meta.en = 50  # Enough

        # Act
        service.pre_process(basic_context, combat_move_attack, basic_actor_snapshot)

        # Assert
        assert basic_context.phases.run_calculator is True
        assert basic_context.result.resource_changes["en"]["cost"] == "-10"

    @patch("apps.game_core.modules.combat.combat_engine.logic.ability_service.GameData")
    def test_pre_process_cost_check_fail(
        self, mock_game_data, service, basic_context, combat_move_attack, basic_actor_snapshot
    ):
        """
        Проверка списания стоимости (нехватка).
        """
        combat_move_attack.payload = MagicMock()
        combat_move_attack.payload.ability_id = "test_ability"

        config = AbilityConfigDTO(
            ability_id="test_ability",
            name_ru="Test",
            description_ru="Desc",
            cost=AbilityCostDTO(energy=100),  # Too much
        )
        mock_game_data.get_ability.return_value = config

        basic_actor_snapshot.meta.en = 50

        # Act
        service.pre_process(basic_context, combat_move_attack, basic_actor_snapshot)

        # Assert
        assert basic_context.phases.run_calculator is False
        assert basic_context.result.skip_reason == "NO_RESOURCE"

    @patch("apps.game_core.modules.combat.combat_engine.logic.ability_service.GameData")
    def test_pre_process_mutations(
        self, mock_game_data, service, basic_context, combat_move_attack, basic_actor_snapshot
    ):
        """
        Проверка применения raw_mutations.
        """
        combat_move_attack.payload = MagicMock()
        combat_move_attack.payload.ability_id = "test_ability"

        config = AbilityConfigDTO(
            ability_id="test_ability", name_ru="Test", description_ru="Desc", raw_mutations={"strength": "+10"}
        )
        mock_game_data.get_ability.return_value = config

        # Act
        service.pre_process(basic_context, combat_move_attack, basic_actor_snapshot)

        # Assert
        # Should be in active abilities
        assert len(basic_actor_snapshot.statuses.abilities) == 1
        ability = basic_actor_snapshot.statuses.abilities[0]
        assert "strength" in ability.modified_keys

        # Should be in raw.attributes or modifiers
        # strength is attribute usually, but let's check where it landed based on logic
        # Logic: checks attributes then modifiers.
        # Assuming strength is in attributes dict in raw (it's empty in fixture but logic creates it)
        assert "strength" in basic_actor_snapshot.raw.attributes
        assert ability.uid in basic_actor_snapshot.raw.attributes["strength"]["temp"]
        assert basic_actor_snapshot.raw.attributes["strength"]["temp"][ability.uid] == "+10"

    @patch("apps.game_core.modules.combat.combat_engine.logic.ability_service.EffectFactory")
    @patch("apps.game_core.modules.combat.combat_engine.logic.ability_service.GameData")
    def test_post_process_apply_effects(
        self, mock_game_data, mock_factory, service, basic_context, combat_move_attack, basic_actor_snapshot
    ):
        """
        Проверка наложения эффектов в post_process.
        """
        # Setup: Add effect to applied_effects queue in result
        effect_data = {"id": "poison", "params": {"power": 1}}
        basic_context.result.applied_effects.append(effect_data)

        effect_config = EffectDTO(
            effect_id="poison", name_en="Poison", name_ru="Яд", type=EffectType.DOT, duration=3, description="Desc"
        )
        mock_game_data.get_effect.return_value = effect_config

        mock_active_effect = MagicMock()
        mock_active_effect.uid = "eff_1"
        mock_factory.create_effect.return_value = (mock_active_effect, {})

        # Act
        service.post_process(basic_context, basic_actor_snapshot, basic_actor_snapshot, combat_move_attack)

        # Assert
        mock_factory.create_effect.assert_called_once()
        assert mock_active_effect in basic_actor_snapshot.statuses.effects
        assert any(e.type == "APPLY_EFFECT" for e in basic_context.result.events)
