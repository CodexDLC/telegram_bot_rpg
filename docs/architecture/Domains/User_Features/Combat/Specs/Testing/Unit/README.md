# Unit Testing Specifications

## 🧪 Resolver Tests
**Component:** `CombatResolver`
**Goal:** Проверка математических формул.

*   `test_accuracy_hit`: Проверка попадания при 100% точности.
*   `test_accuracy_miss`: Проверка промаха.
*   `test_crit_calculation`: Проверка множителя крита.
*   `test_damage_mitigation`: Проверка работы брони и резистов.

## 🧪 Context Builder Tests
**Component:** `ContextBuilder`
**Goal:** Проверка сборки флагов.

*   `test_build_flags_from_intent`: Превращение MoveDTO в PipelineFlags.
*   `test_dual_wield_detection`: Определение второй руки.

## 🧪 Ability Service Tests
**Component:** `AbilityService`
**Goal:** Проверка эффектов и стоимости.

*   `test_cost_payment`: Списание HP/Energy.
*   `test_effect_application`: Создание ActiveAbilityDTO.

## 🧪 Feint Service Tests
**Component:** `FeintService`
**Goal:** Проверка логики карт.

*   `test_deck_assembly`: Сбор колоды из экипировки.
*   `test_hand_refill`: Алгоритм заполнения руки.
