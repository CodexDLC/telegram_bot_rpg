# Ability Service Specification (RBC v2.0)

**File:** `apps/game_core/modules/combat/services/ability_service.py`
**Responsibility:** Управление логикой скиллов и эффектов. Хуки до и после математики.

## 1. Концепция
Сервис не считает урон. Он модифицирует условия боя на основе пассивок, баффов и свойств скилла.

*   **Pre-Calc:** Изменяет вводные данные (статы/флаги) до того, как Калькулятор сделает Roll.
*   **Post-Calc:** Анализирует результат (Крит/Блок) после Калькулятора и генерирует сайд-эффекты (Кровотечение, Стан, Хил).

---

## 2. API Methods

### A. Pre-Calculation (The Modifier)
**Method:** `pre_calculate(source_snapshot, target_snapshot, skill_payload) -> dict`

Вызывается Оркестратором перед `CombatCalculator.calculate_hit`.

**Logic:**
1.  **Check Active Effects:** Проходит по списку `source.effects`.
    *   *Пример:* Если висит бафф "Ярость" -> добавляет в возвращаемые флаги `damage_mult: 1.5`.
    *   *Пример:* Если висит дебафф "Слепота" -> добавляет `force_miss: True` (или снижает hit_rate).
2.  **Check Skill Properties:** Смотрит в `skill_payload` (конфиг скилла).
    *   *Пример:* Скилл "Точный выстрел" -> `ignore_dodge: True`.
    *   *Пример:* Скилл "Удар щитом" -> `override_damage_type: "blunt"`.

**Return (Flags):** Словарь флагов, который уйдет в CombatCalculator (например, `ignore_armor`, `bonus_crit`, `damage_mult`).

### B. Post-Calculation (The Trigger)
**Method:** `post_calculate(ctx, source, target, calculation_result) -> None`

Вызывается Оркестратором сразу после получения цифр от Калькулятора.

**Logic:**
1.  **Event Matching:** Сверяет флаги результата (`is_crit`, `is_blocked`, `is_dodged`) с триггерами абилок и пассивок.
2.  **Apply Side-Effects:** Если триггер сработал — создает новые эффекты.

**Сценарии (Use Cases):**
*   **On Crit:** `if result['is_crit']:`
    *   Проверить пассивку "Глубокие раны".
    *   Действие: `self.apply_effect(target, "bleeding_dot")`.
*   **On Block:** `if result['is_blocked']:`
    *   Проверить щит "Шипы". (Хотя шипы мы вынесли в калькулятор как цифру, здесь можно наложить эффект "Ошеломление" на атакующего).
*   **On Hit (General):**
    *   Скилл "Отравленный кинжал".
    *   Действие: `self.apply_effect(target, "poison", duration=3)`.

---

## 3. Вспомогательные методы (Effect Management)
Эти методы используются внутри Pre/Post логики.

*   `apply_effect(target_ctx, effect_id, duration, payload)`:
    *   Создает объект `ActorEffect`.
    *   Добавляет его в `target.effects` (в памяти контекста).
    *   Логирует: "Наложен эффект {id}".

*   `process_periodic(actor_ctx)`:
    *   Вызывается в конце хода (или начале).
    *   Тикает доты/хоты.

---

## 4. Integration Flow

```python
# Pseudo-code usage in Orchestrator

# 1. PRE-CALC
flags = AbilityService.pre_calculate(source, target, skill_config)
# flags = {'bonus_crit': 50, 'ignore_block': True}

# 2. MATH
result = CombatCalculator.calculate_hit(..., flags=flags)
# result = {'damage': 100, 'is_crit': True, ...}

# 3. POST-CALC
AbilityService.post_calculate(ctx, source, target, result)
# Внутри: увидел is_crit -> наложил эффект кровотечения на target
```