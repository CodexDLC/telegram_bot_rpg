from unittest.mock import patch

import pytest

from backend.domains.user_features.combat.combat_engine import FeintService
from backend.resources.game_data.feints.schemas import FeintConfigDTO, FeintCostDTO


@pytest.mark.combat
class TestFeintService:
    @patch("apps.game_core.modules.combat.combat_engine.mechanics.feint_service.get_feint_config")
    def test_refill_hand_logic(self, mock_get_config, basic_actor_snapshot):
        """
        Проверка заполнения руки до лимита (3).
        """
        # Setup
        # Arsenal: ["feint_hit", "feint_crit"]
        # Tokens: {"tactics": 5}
        # Cost: 1 tactic

        config = FeintConfigDTO(
            feint_id="feint_hit", name_ru="Hit", description_ru="...", cost=FeintCostDTO(tactics={"tactics": 1})
        )
        mock_get_config.return_value = config

        actor_meta = basic_actor_snapshot.meta
        actor_meta.feints.hand = {}  # Empty hand

        # Act
        FeintService.refill_hand(actor_meta)

        # Assert
        # Hand should be full (limited by arsenal size 2 or MAX_HAND_SIZE 3)
        # Arsenal has 2 items. Both affordable.
        # Logic picks random.
        assert actor_meta.feints.get_hand_size() > 0
        assert actor_meta.feints.get_hand_size() <= 3

        # Tokens should be deducted
        # If we added 2 cards * 1 cost = 2 tokens spent.
        # Initial 5 -> 3.
        spent = 5 - actor_meta.tokens["tactics"]
        assert spent == actor_meta.feints.get_hand_size()

    @patch("apps.game_core.modules.combat.combat_engine.mechanics.feint_service.get_feint_config")
    def test_refill_hand_not_enough_tokens(self, mock_get_config, basic_actor_snapshot):
        """
        Проверка: Финт не берется, если нет токенов.
        """
        config = FeintConfigDTO(
            feint_id="feint_expensive",
            name_ru="Exp",
            description_ru="...",
            cost=FeintCostDTO(tactics={"tactics": 10}),  # Expensive
        )
        mock_get_config.return_value = config

        actor_meta = basic_actor_snapshot.meta
        actor_meta.feints.arsenal = ["feint_expensive"]
        actor_meta.tokens["tactics"] = 5
        actor_meta.feints.hand = {}

        # Act
        FeintService.refill_hand(actor_meta)

        # Assert
        assert actor_meta.feints.get_hand_size() == 0
        assert actor_meta.tokens["tactics"] == 5  # No change

    def test_return_to_hand(self, basic_actor_snapshot):
        """
        Проверка возврата карты в руку.
        """
        actor_meta = basic_actor_snapshot.meta
        cost = {"tactics": 1}

        FeintService.return_to_hand(actor_meta, "feint_returned", cost)

        assert actor_meta.feints.is_in_hand("feint_returned")
        assert actor_meta.feints.hand["feint_returned"] == cost
