# 🛠️ Task: Finalize Basic Combat Pipeline

[⬅️ Назад: Roadmap](../Roadmap.md)

---

## 🎯 Цель
Завершить реализацию базового цикла боя ("Happy Path"), устранив заглушки (`pass`, `TODO`) в ключевых сервисах Engine.
Обеспечить соответствие кода обновленной документации (V2).

## 📋 Подзадачи (Subtasks)

### 1. 📚 Documentation & Audit (Документация)
- [x] **Сравнить Code vs Docs:** Проведен аудит `MechanicsService` и `AbilityService`. Выявлены критические заглушки (Effects, Tokens, Feints).
- [ ] **Доработать Specs:**
    - [ ] Обновить `Mechanics_Service.md`: Детально описать алгоритм начисления токенов и структуру XP Buffer.
    - [ ] Обновить `Ability_Service.md`: Расписать процесс создания эффектов (`ActiveAbilityDTO`) в методе `_apply_effect`.

### 2. 🔧 Mechanics Service Implementation (Механика)
- [ ] **Token Awards:** Реализовать логику начисления токенов (`tokens_awarded_attacker/defender`) в `Actor.meta.tokens`.
- [ ] **XP Registration:** Реализовать запись событий в `Actor.xp_buffer` (структура: `{event_type: count}`).
- [ ] **Sustain & Thorns:** Реализовать методы для Lifesteal и Reflected Damage в `_apply_source_changes`.
- [ ] **Feint Integration:** Добавить вызов `FeintService.update_hand_state(actor)` в конце обработки.

### 3. ✨ Ability Service Implementation (Эффекты)
- [ ] **Effect Factory:** Реализовать метод `_apply_effect`:
    - [ ] Использовать `GameData.get_effect_config(id)` для получения шаблона.
    - [ ] Создавать объект `ActiveAbilityDTO` (генерация UID, расчет длительности).
    - [ ] Добавлять эффект в список `Actor.active_abilities`.
- [ ] **Feint Validation:** Реализовать вызов `FeintService.validate_card` в `pre_process`.

### 4. 🃏 Feint Service & Data (Финты)
- [ ] **Game Data:** Создать `feints/definitions/debug.py` с тестовым финтом.
- [ ] **Feint Service:** Реализовать методы `calculate_pool`, `fill_hand`, `validate_card`.

### 5. ⚙️ Pipeline Core (Ядро)
- [ ] **Error Handling:** Заменить пустой возврат `InteractionResultDTO()` при ошибке/смерти на корректный DTO с флагом `is_interrupted` или `is_dead`.
- [ ] **Logging:** Убедиться, что все критические изменения состояния логируются.

## 🔗 Связанные файлы
*   `apps/game_core/modules/combat/combat_engine/logic/mechanics_service.py`
*   `apps/game_core/modules/combat/combat_engine/logic/ability_service.py`
*   `apps/game_core/modules/combat/combat_engine/logic/feint_service.py`
