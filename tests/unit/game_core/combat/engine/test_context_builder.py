from unittest.mock import patch

import pytest

from src.backend.domains.user_features.combat.combat_engine.logic.context_builder import ContextBuilder
from src.backend.domains.user_features import CombatMoveDTO


@pytest.mark.combat
class TestContextBuilder:
    def test_build_flags_magic(self, basic_actor_snapshot):
        """
        Проверка: strategy='instant' -> source_type='magic'.
        """
        move = CombatMoveDTO(move_id="m1", char_id=1, strategy="instant", payload={"ability_id": "fireball"})

        ctx = ContextBuilder.build_context(basic_actor_snapshot, None, move)

        assert ctx.flags.meta.source_type == "magic"

    def test_build_flags_weapon(self, basic_actor_snapshot):
        """
        Проверка: strategy='exchange' -> source_type='main_hand' + weapon_class.
        """
        # Loadout: main_hand = skill_swords
        basic_actor_snapshot.loadout.layout = {"main_hand": "skill_swords"}

        move = CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload={"target_id": 2})

        ctx = ContextBuilder.build_context(basic_actor_snapshot, None, move)

        assert ctx.flags.meta.source_type == "main_hand"
        assert ctx.flags.meta.weapon_class == "swords"

    @patch("apps.game_core.modules.combat.combat_engine.logic.context_builder.MathCore")
    def test_dual_wield_trigger_success(self, mock_math, basic_actor_snapshot):
        """
        Проверка: Если есть off_hand оружие и прок -> trigger_offhand_attack.
        """
        # Setup
        basic_actor_snapshot.loadout.layout = {
            "main_hand": "skill_swords",
            "off_hand": "skill_daggers",  # Valid weapon
        }
        basic_actor_snapshot.skills.skill_dual_wield = 50.0

        mock_math.check_chance.return_value = True  # Proc

        move = CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload={"target_id": 2})

        # Act
        ctx = ContextBuilder.build_context(basic_actor_snapshot, None, move)

        # Assert
        assert ctx.result.chain_events.trigger_offhand_attack is True

    def test_dual_wield_trigger_fail_shield(self, basic_actor_snapshot):
        """
        Проверка: Если off_hand это щит -> trigger_offhand_attack False.
        """
        basic_actor_snapshot.loadout.layout = {
            "main_hand": "skill_swords",
            "off_hand": "skill_shield",  # Shield
        }

        move = CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload={"target_id": 2})

        ctx = ContextBuilder.build_context(basic_actor_snapshot, None, move)

        assert ctx.result.chain_events.trigger_offhand_attack is False

    def test_defense_flags(self, basic_actor_snapshot):
        """
        Проверка: Анализ защиты цели (Armor Type).
        """
        target = basic_actor_snapshot.model_copy(deep=True)
        target.loadout.layout = {"body": "skill_heavy_armor", "off_hand": "skill_shield"}

        move = CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload={"target_id": 2})

        ctx = ContextBuilder.build_context(basic_actor_snapshot, target, move)

        assert ctx.flags.mastery.shield_reflect is True
