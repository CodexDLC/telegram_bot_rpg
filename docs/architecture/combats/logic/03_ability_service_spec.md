# Ability Service Specification (RBC v3.0)

**File:** `apps/game_core/modules/combat/services/ability_service.py`
**Responsibility:** Управление жизненным циклом абилок, эффектов и временных модификаторов.

## 1. Концепция
Сервис управляет двумя аспектами "магии":
1.  **Stat Modifiers (Temp Layer):** Изменения характеристик (Сила, Урон), которые живут в `:raw...temp`.
2.  **Resource Impact (Active Abilities):** Периодические изменения ресурсов (HP, EN), которые живут в `:active_abilities`.

---

## 2. Управление Временем (Time Management)

### A. Lifecycle Check (Cleanup)
Вызывается в начале каждого тика Воркера (до расчета статов).

**Алгоритм:**
1.  Проходит по списку `actor.active_abilities`.
2.  Сравнивает `ability.expire_at_exchange` с текущим `actor.state.exchange_count`.
3.  **Если время вышло:**
    *   Удаляет запись из `active_abilities`.
    *   **Важно:** Ищет и удаляет связанные ключи в `actor.raw.attributes...temp` и `actor.raw.modifiers...temp`.
    *   *Как ищет?* Ключи в `temp` должны содержать ID абилки (например, `ability:poison_cloud`).

### B. Apply Periodic (Impact)
Вызывается на Фазе 4 (Mechanics), но данные готовит AbilityService.
См. `MechanicsService` для деталей применения.

---

## 3. API Methods

### A. Apply Ability (Наложение)
**Method:** `apply_ability(target_ctx, ability_id, duration, payload)`

**Алгоритм:**
1.  **Load Config:** Загружает конфиг абилки (статы, импакт).
2.  **Create Active Record:**
    *   Создает запись в `active_abilities`.
    *   Устанавливает `expire_at_exchange = current + duration`.
    *   Записывает `impact` (например, `{"hp": -10}`).
3.  **Inject Temp Stats:**
    *   Если абилка дает статы (например, +10 Силы), пишет их в `target.raw.attributes.strength.temp["ability:{id}"] = "+10"`.
4.  **Log:** "Наложен эффект {id}".

### B. Pre-Calculation (The Modifier)
**Method:** `pre_calculate(source_snapshot, target_snapshot, skill_payload) -> dict`

Вызывается Оркестратором перед `CombatCalculator.calculate_hit`.
*Теперь этот метод проще, так как статы уже учтены в StatsEngine через temp-слой.*
Он нужен только для **Флагов** (например, `ignore_block`, `always_crit`), которые нельзя выразить цифрами.

**Logic:**
1.  Проверяет наличие специфических абилок в `active_abilities`.
2.  Возвращает флаги.

### C. Post-Calculation (The Trigger)
**Method:** `post_calculate(ctx, source, target, calculation_result) -> None`

Вызывается Оркестратором сразу после получения цифр от Калькулятора.

**Logic:**
1.  **Event Matching:** Сверяет флаги результата (`is_crit`, `is_blocked`) с триггерами пассивок.
2.  **Apply Side-Effects:** Вызывает `apply_ability`.

---

## 4. Разделение Ответственности

| Тип Эффекта | Где хранится | Кто обрабатывает | Пример |
| :--- | :--- | :--- | :--- |
| **Stat Mod** | `:raw...temp` | `StatsEngine` | +10 Strength, *1.5 Damage |
| **Override** | `:raw...temp` | `StatsEngine` | Speed = 0 (Root) |
| **DoT / HoT** | `:active_abilities.impact` | `MechanicsService` | -10 HP/turn (Poison) |
| **Flag** | In-Memory Logic | `AbilityService.pre_calc` | Ignore Armor, Cannot Miss |
