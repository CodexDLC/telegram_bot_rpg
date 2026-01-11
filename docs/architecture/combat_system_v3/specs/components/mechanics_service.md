# Component: MechanicsService

⬅️ [Назад](../README.md) | 🏠 [Документация](../../../../README.md)

> ⚠️ **NOTE:** Этот документ описывает текущую реализацию, но может потребовать улучшений в будущем (особенно в части XP и токенов).

**File:** `apps/game_core/modules/combat/services/mechanics_service.py`
**Responsibility:** Мутация стейта (HP, EN, Flags, Tokens).

## 1. Принципы
*   **State Mutator:** Единственное место изменения `actor.state`.
*   **Token Manager:** Управление токенами (Дар, Комбо).
*   **XP Registrar:** Регистрация действий для прокачки.

---

## 2. API Methods

### A. Apply Interaction Result (Главный метод)
**Method:** `apply_damage_result(ctx, source, target, result: dict)`

**Алгоритм:**
1.  **Damage & Sustain:**
    *   `target.hp -= result['damage_final']`
    *   `source.hp += result['lifesteal']`
    *   `source.hp -= result['thorns_damage']`
2.  **Token Update (New!):**
    *   **Action Tokens:** Берет токены из `result['tokens_atk']` (например, `{"parry": 1}`) и добавляет в `source.state.tokens`.
    *   **Gift Token (Дар):** Автоматически добавляет `+1` к `source.state.tokens['gift']` и `target.state.tokens['gift']` (за факт участия в размене).
3.  **XP Registration (New!):**
    *   Инкрементит счетчики в `source.xp_buffer` и `target.xp_buffer` на основе флагов результата.
    *   *Пример:* `if result['is_crit']: source.xp_buffer['crit_hits'] += 1`.
    *   *Важно:* Не проверяет экипировку. Просто фиксирует факт.
4.  **Finalize Status:**
    *   `self._check_death(target)`
    *   `self._check_death(source)`

### B. Apply Periodic (Фаза 4)
**Method:** `apply_periodic_effects(actor, log_service)`
*   Применяет `impact` из `active_abilities`.
*   Логирует через `CombatLogService`.

### C. Apply Cost (Оплата)
**Method:** `pay_resource_cost(actor, cost_en: int, cost_hp: int)`
*   Списывает ресурсы.

---

## 3. XP System (Registration vs Calculation)
*   **В бою (MechanicsService):** Мы только **регистрируем** события ("Уклонился", "Ударил мечом").
    *   Пишем в `xp_buffer` (RedisJSON).
*   **После боя (Post-Combat):** Сервис наград берет `xp_buffer`, смотрит на `raw.equipment` (что было в руках) и начисляет опыт в конкретные ветки (Мечи, Уклонение).
