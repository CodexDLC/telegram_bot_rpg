# Mechanics Service Specification (RBC v2.0)

**File:** `apps/game_core/modules/combat/services/mechanics_service.py`
**Responsibility:** Мутация стейта (HP, EN, Flags) на основе рассчитанных цифр. "Бухгалтер" боевой системы.

## 1. Принципы
*   **State Mutator:** Это единственное место, где происходит `actor.state.hp -= value`.
*   **No Random:** Здесь нет кубиков. Весь рандом остался в Калькуляторе.
*   **Safety:** Следит, чтобы HP не ушло в минус (или ставит 0), и проставляет флаг `is_dead`.

---

## 2. API Methods

### A. Apply Interaction Result (Главный метод)
**Method:** `apply_damage_result(ctx, source, target, result: dict)`

Применяет итоги физического размена (Exchange).

**Алгоритм:**
1.  **Target Damage:**
    *   `target.hp -= result['damage_final']`
    *   `target.shield -= result['shield_dmg']` (если есть механика щитов)
    *   Log: "Получен урон: 150".
2.  **Source Sustain (Vampirism):**
    *   Если `result['lifesteal_amount'] > 0`:
        *   `source.hp = min(source.max_hp, source.hp + result['lifesteal'])`
        *   Log: "Вампиризм: +15 HP".
3.  **Source Penalty (Thorns):**
    *   Если `result['thorns_damage'] > 0`:
        *   `source.hp -= result['thorns_damage']`
        *   Log: "Шипы: -10 HP".
4.  **Token Update:**
    *   Добавляет токены из `result['tokens_atk']` атакующему.
    *   Добавляет токены из `result['tokens_def']` защитнику.
5.  **Finalize Status:**
    *   Вызывает `self._check_death(target)`
    *   Вызывает `self._check_death(source)` (он мог убиться об шипы).

### B. Apply Cost (Оплата)
**Method:** `pay_resource_cost(actor, cost_en: int, cost_hp: int)`

Вызывается Оркестратором перед действием (или после, если у нас постоплата).

**Алгоритм:**
*   `actor.en -= cost_en`
*   `actor.hp -= cost_hp` (для магии крови)
*   Если ресурсов не хватает — по идее это должно было отсеяться на этапе Валидации, но здесь можно сделать clamp (не уводить в минус).

### C. Death Check (Мрачный Жнец)
**Method:** `_check_death(actor)`

**Алгоритм:**
*   `if actor.hp <= 0:`
    *   `actor.hp = 0`
    *   `actor.is_dead = True`
    *   Log: "☠️ Боец пал!"
    *   (Опционально) Очистить список очередей ходов для этого актера, чтобы труп не бил.

---

## 3. Схема взаимодействия в Оркестраторе

```python
# Внутри CombatExchangeOrchestrator

async def process_exchange(self, ctx, task):
    # 1. SETUP
    source = ctx.get_actor(task.source_id)
    target = ctx.get_actor(task.target_id)
    
    # 2. PRE-CALC (Ability Service)
    # "Ярость: след удар крит"
    flags = AbilityService.pre_calculate(source, target) 
    
    # 3. MATH (Calculator)
    # "Урон 100, Крит, Вампиризм 10" (State НЕ меняется)
    result = CombatCalculator.calculate_hit(..., flags=flags)
    
    # 4. POST-CALC (Ability Service)
    # "Крит прошел -> Наложить кровотечение" (State меняется: +Effect)
    AbilityService.post_calculate(ctx, source, target, result)
    
    # 5. APPLY (Mechanics Service)
    # "HP -100, HP +10, Проверка смерти" (State меняется: HP/Dead)
    MechanicsService.apply_damage_result(ctx, source, target, result)
    
    # 6. LOGS
    # Оркестратор забирает логи из ctx.pending_logs и готовит к отправке
```