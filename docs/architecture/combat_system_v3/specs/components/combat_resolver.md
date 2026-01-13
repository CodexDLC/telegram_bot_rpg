# Component: CombatResolver

⬅️ [Назад](../README.md) | 🏠 [Документация](../../../../README.md)

**File:** `apps/game_core/modules/combat/combat_engine/logic/combat_resolver.py`
**Type:** Stateless Math Engine.

## 1. Ответственность
`CombatResolver` — это чистая математическая функция, которая принимает статы двух бойцов и контекст, а возвращает результат их взаимодействия (урон, уворот, крит).

*   **Stateless:** Не хранит состояние.
*   **Pure Logic:** Не лезет в базу, не кидает ивенты.
*   **Flag-Driven:** Логика управляется флагами из `PipelineContextDTO`.

## 2. Входные и Выходные данные

### Input
*   `attacker_stats: ActorStats` — Характеристики атакующего.
*   `defender_stats: ActorStats` — Характеристики защитника.
*   `context: PipelineContextDTO` — Контекст текущего удара (флаги, модификаторы, триггеры).

### Output
*   `InteractionResultDTO` — Результат расчета.
    *   `damage_final`: Итоговый урон.
    *   `is_crit`, `is_dodged`, `is_parried`, `is_blocked`: Флаги результата.
    *   `tokens_awarded_attacker`: Токены, полученные атакующим.
    *   `tokens_awarded_defender`: Токены, полученные защитником.

## 3. Алгоритм расчета (Pipeline)

Расчет происходит пошагово. Каждый шаг может прервать цепочку (например, если случился уворот, урон не считается).

### Step 1: Accuracy Roll (Точность)
Проверка, попал ли удар в принципе.
*   **Base:** `accuracy` атакующего.
*   **Logic:** Если `force.miss` -> Miss. Если `force.hit` -> Hit.

### Step 2: Crit Roll (Крит)
Определяет, будет ли удар критическим.
*   **Base:** `crit_chance` атакующего.
*   **Logic:** Если крит прошел, ставится флаг `is_crit`.
*   *Важно:* Крит может влиять на дальнейшие проверки (например, Undodgeable Crit).

### Step 3: Evasion Roll (Уклонение)
Проверка, увернулся ли защитник.
*   **Base:** `dodge_chance` защитника.
*   **Counter:** `anti_dodge_chance` атакующего.
*   **Logic:** Если `is_dodged` -> Урон 0, конец расчета.

### Step 4: Parry Roll (Парирование)
Проверка, парировал ли защитник удар оружием.
*   **Base:** `parry_chance` защитника.
*   **Logic:** Если `is_parried` -> Урон 0 (или снижен), возможна контратака.

### Step 5: Block Roll (Блок щитом)
Проверка блока щитом.
*   **Base:** `shield_block_chance`.
*   **Logic:** Если `is_blocked` -> Урон 0 (полный блок) или частичное поглощение.

### Step 6: Damage Calculation (Урон)
Если все проверки пройдены, считается урон.
1.  **Base Damage:** `random(min, max)`.
2.  **Crit Multiplier:** Если был крит (x1.5, x2.0 и т.д.).
3.  **Mitigation:**
    *   **Physical:** `(Damage * (1 - Resist)) - FlatArmor`.
    *   **Elemental:** `Damage * (1 - Resist)`.
    *   **Pure:** Игнорирует резисты.

## 4. Триггеры (Triggers)

### 4.1. Концепция

Резолвер обрабатывает триггеры, которые были **активированы** до начала расчёта:
- Context Builder активирует триггеры оружия
- Ability Service активирует триггеры скиллов/финтов

Resolver **НЕ ЗНАЕТ** источник триггера. Он просто проверяет флаги `ctx.triggers.*` и применяет правила из `TRIGGER_RULES`.

### 4.2. Обработка

На каждом событии (`ON_HIT`, `ON_CRIT`, `ON_DODGE`, ...) вызывается:
```python
_resolve_triggers(ctx, result, step_key="ON_CRIT")
```

**Алгоритм:**
1. Получить правила для события: `rules = TRIGGER_RULES[step_key]`
2. Для каждого триггера в правилах:
   - Проверить активен ли: `ctx.triggers.<name> == True`
   - Проверить шанс: `MathCore.check_chance(rule["chance"])`
   - Применить мутации: `setattr(ctx.stages, key, value)`

### 4.3. Мутации

Триггеры могут менять:

**A) Флаги пайплайна:**
```python
"mutations": {
    "check_evasion": False,  # ctx.stages.check_evasion
    "crit_damage_boost": True  # ctx.flags.formula.crit_damage_boost
}
```

**B) Модификаторы:**
```python
"mutations": {
    "weapon_effect_value": 3.0  # ctx.mods.weapon_effect_value
}
```

**C) Инструкции для Ability Service:**
```python
# В _step_calculate_damage()
if ctx.triggers.trigger_bleed and res.is_crit:
    result.ability_flags.apply_bleed = True
    result.ability_flags.pending_effect_data = {
        "bleed_strength": 0.3,
        "duration": 3
    }
```

### 4.4. Пример: Меч с кровотечением

**1. Context Builder:**
```python
weapon.triggers = ["trigger_bleed"]
ctx.triggers.trigger_bleed = True  # Активация
```

**2. Resolver (Crit Roll):**
```python
if MathCore.check_chance(crit_chance):
    res.is_crit = True
    _resolve_triggers(ctx, res, "ON_CRIT")
```

**3. Resolver (_resolve_triggers):**
```python
rules = TRIGGER_RULES["ON_CRIT"]["trigger_bleed"]
if ctx.triggers.trigger_bleed:
    # Применяем мутации
    ctx.flags.formula.crit_damage_boost = rules["mutations"]["crit_damage_boost"]
```

**4. Resolver (_calculate_damage):**
```python
if res.is_crit and ctx.triggers.trigger_bleed:
    result.ability_flags.apply_bleed = True
    result.ability_flags.pending_effect_data = {
        "bleed_damage": result.damage_final * 0.3,
        "duration": 3
    }
```

**5. Ability Service (Post-Calc):**
```python
if result.ability_flags.apply_bleed:
    apply_bleed_effect(target, result.ability_flags.pending_effect_data)
```
