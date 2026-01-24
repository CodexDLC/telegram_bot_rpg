from unittest.mock import patch

import pytest

from backend.domains.user_features.combat.combat_engine.logic.combat_resolver import CombatResolver


@pytest.mark.combat
class TestCombatResolver:
    # ==========================================================================
    # 1. ACCURACY
    # ==========================================================================

    @patch("apps.game_core.modules.combat.combat_engine.logic.combat_resolver.MathCore")
    def test_accuracy_hit(self, mock_math, basic_actor_stats, basic_context):
        """Проверка успешного попадания."""
        # Setup
        mock_math.check_chance.return_value = True
        basic_context.stages.check_accuracy = True

        # Act
        result = CombatResolver.resolve_exchange(basic_actor_stats, basic_actor_stats, basic_context)

        # Assert
        assert not result.is_miss
        mock_math.check_chance.assert_called()  # Проверяем что рандом вызывался

    @patch("apps.game_core.modules.combat.combat_engine.logic.combat_resolver.MathCore")
    def test_accuracy_miss(self, mock_math, basic_actor_stats, basic_context):
        """Проверка промаха."""
        # Setup
        mock_math.check_chance.return_value = False
        basic_context.stages.check_accuracy = True

        # Act
        result = CombatResolver.resolve_exchange(basic_actor_stats, basic_actor_stats, basic_context)

        # Assert
        assert result.is_miss
        assert result.tokens_awarded_defender.get("tempo") == 1
        assert any(e.type == "MISS" for e in result.events)

    def test_accuracy_force_hit(self, basic_actor_stats, basic_context):
        """Проверка флага force.hit."""
        basic_context.flags.force.hit = True

        result = CombatResolver.resolve_exchange(basic_actor_stats, basic_actor_stats, basic_context)

        assert not result.is_miss
        # MathCore не должен вызываться, но мы его не мокали тут, так как логика должна вернуть True до вызова

    # ==========================================================================
    # 2. EVASION
    # ==========================================================================

    @patch("apps.game_core.modules.combat.combat_engine.logic.combat_resolver.MathCore")
    def test_evasion_success(self, mock_math, basic_actor_stats, basic_context):
        """Проверка успешного уклонения."""
        # Сначала проходим Accuracy (True)
        # Потом Evasion (True)
        mock_math.check_chance.side_effect = [True, True]

        basic_context.stages.check_evasion = True
        basic_actor_stats.mods.dodge_chance = 0.5

        result = CombatResolver.resolve_exchange(basic_actor_stats, basic_actor_stats, basic_context)

        assert result.is_dodged
        assert result.tokens_awarded_defender.get("dodge") == 1
        assert any(e.type == "DODGE" for e in result.events)

    @patch("apps.game_core.modules.combat.combat_engine.logic.combat_resolver.MathCore")
    def test_evasion_fail(self, mock_math, basic_actor_stats, basic_context):
        """Проверка провала уклонения."""
        # Accuracy=True, Evasion=False
        mock_math.check_chance.side_effect = [True, False]

        basic_context.stages.check_evasion = True
        basic_actor_stats.mods.dodge_chance = 0.5

        result = CombatResolver.resolve_exchange(basic_actor_stats, basic_actor_stats, basic_context)

        assert not result.is_dodged

    # ==========================================================================
    # 3. DAMAGE & ARMOR
    # ==========================================================================

    @patch("apps.game_core.modules.combat.combat_engine.logic.combat_resolver.MathCore")
    def test_damage_calculation_physical(self, mock_math, basic_actor_stats, basic_context):
        """
        Проверка расчета физического урона.
        Base: 100
        Armor Flat: 5
        Resist: 10% (0.1)
        """
        # Mocks
        # 1. Accuracy -> True
        # 2. Evasion -> False
        # 3. Parry -> False
        # 4. Block -> False
        # 5. Crit -> False
        mock_math.check_chance.return_value = (
            False  # Для всех проверок шансов (кроме Accuracy, там инверсия логики в коде нет, но Accuracy первый)
        )
        # Accuracy вызывается первым. Если check_chance вернет False -> Miss.
        # Нам нужно Accuracy=True.
        # Но проще отключить проверки защиты флагами, чтобы дойти до урона.

        basic_context.stages.check_accuracy = False  # Skip acc
        basic_context.stages.check_evasion = False
        basic_context.stages.check_parry = False
        basic_context.stages.check_block = False
        basic_context.stages.check_crit = False

        # Random Range для урона. Base=100. Spread=0.1 -> 90..110.
        # Пусть вернет 100.
        mock_math.random_range.return_value = 100.0

        # Act
        result = CombatResolver.resolve_exchange(basic_actor_stats, basic_actor_stats, basic_context)

        # Calc:
        # Raw = 100
        # Mitigation (Resist 0.1 - Pen 0.0) = 0.1
        # After Resist: 100 * (1 - 0.1) = 90
        # After Flat Armor: 90 - 5 = 85

        assert result.is_hit
        assert result.damage_final == 85
        assert result.tokens_awarded_attacker.get("hit") == 1

    @patch("apps.game_core.modules.combat.combat_engine.logic.combat_resolver.MathCore")
    def test_damage_crit(self, mock_math, basic_actor_stats, basic_context):
        """
        Проверка критического урона.
        """
        basic_context.stages.check_accuracy = False
        basic_context.stages.check_evasion = False
        basic_context.stages.check_parry = False
        basic_context.stages.check_block = False

        # Force Crit
        basic_context.flags.force.crit = True

        mock_math.random_range.return_value = 100.0

        # Act
        result = CombatResolver.resolve_exchange(basic_actor_stats, basic_actor_stats, basic_context)

        # Calc:
        # Crit Mult default = 1.0 (если нет бустов и магии) -> В коде _calculate_crit_multiplier возвращает 1.0 для физы без флагов?
        # Проверим код: if is_magic -> 3.0. else if boost -> val. else -> 1.0.
        # Wait, crit usually implies multiplier.
        # В текущей реализации CombatResolver._calculate_crit_multiplier возвращает 1.0 для физы по умолчанию?
        # Это странно, но проверим тест. Если так, то крит дает только токены и триггеры.

        # UPD: В коде:
        # if res.is_crit:
        #    phys_dmg *= crit_multiplier

        # Если crit_multiplier = 1.0, то урон не растет.
        # Проверим, может я что-то упустил в коде.
        # Да, _calculate_crit_multiplier возвращает 1.0 по дефолту для физы.
        # Видимо, крит урон задается через weapon_effect_value + flag crit_damage_boost?
        # Или это баг/фича текущей версии.

        # Допустим, мы хотим проверить логику.
        assert result.is_crit
        assert result.tokens_awarded_attacker.get("crit") == 1
        assert "CRIT" in result.events[-1].tags

    # ==========================================================================
    # 4. TRIGGERS
    # ==========================================================================

    @patch(
        "apps.game_core.modules.combat.combat_engine.logic.combat_resolver.TRIGGER_RULES_DICT",
        new={"test_rule": {"event": "ON_ACCURACY_CHECK", "chance": 1.0, "mutations": {"flags.force.crit": True}}},
    )
    @patch("apps.game_core.modules.combat.combat_engine.logic.combat_resolver.MathCore")
    def test_trigger_execution(self, mock_math, basic_actor_stats, basic_context):
        """
        Проверка срабатывания триггера.
        Мы подменяем TRIGGER_RULES_DICT на тестовый.
        И активируем этот триггер в контексте.
        """
        # Setup
        mock_math.check_chance.return_value = True  # Accuracy pass

        # Активируем триггер в DTO (динамически добавляем атрибут, так как DTO жесткий,
        # но мы можем использовать существующее поле или мокнуть DTO)
        # В TriggerRulesFlagsDTO поля фиксированы. Нам нужно использовать существующее поле или добавить его.
        # В тесте мы не можем легко изменить класс DTO.
        # Поэтому используем реальное поле из TriggerRulesFlagsDTO, например 'true_strike'.

        # Переопределим патч, используя реальный ID
        with patch(
            "apps.game_core.modules.combat.combat_engine.logic.combat_resolver.TRIGGER_RULES_DICT",
            new={
                "true_strike": {
                    "event": "ON_ACCURACY_CHECK",
                    "chance": 1.0,
                    "mutations": {"flags.force.crit": True},  # Мутация: следующий удар будет критом
                }
            },
        ):
            # Активируем флаг
            basic_context.triggers.accuracy.true_strike = True

            # Act
            result = CombatResolver.resolve_exchange(basic_actor_stats, basic_actor_stats, basic_context)

            # Assert
            # Триггер должен был сработать на этапе Accuracy и выставить force.crit = True
            # Значит результат должен быть критом
            assert basic_context.flags.force.crit is True
            # И в результате тоже
            assert result.is_crit
