# Component: CombatManager

⬅️ [Назад](../../README.md) | 🏠 [Документация](../../../../../README.md)

**File:** `apps/common/services/redis/manager/combat_manager.py`
**Layer:** Low-Level Redis Driver.
**Responsibility:** Прямой доступ к Redis, инкапсуляция ключей и атомарных операций (Lua).

## 1. Ключевые функции

### A. Session Management
*   `create_session_batch`: Создает структуру сессии (Meta, Targets, Actors) за один Pipeline.
*   `universal_hot_join`: Атомарно добавляет нового участника в активный бой (обновляет Meta и Targets).

### B. Atomic Moves (Lua Scripts)
*   `register_exchange_move_atomic`:
    1.  Проверяет наличие цели в очереди `targets`.
    2.  Удаляет цель (POP).
    3.  Записывает мув.
    *   *Защита от спама:* Если цели нет, мув не регистрируется.
*   `register_moves_batch_atomic`: То же самое, но для пачки ходов (AI).

### C. Queue Management
*   `transfer_intents_to_actions`: Атомарно переносит мувы из буфера игрока в системную очередь `q:actions`.
*   `check_and_lock_busy_for_collector`: Fencing Token для защиты от двойного запуска воркера.

### D. Batch Loading
*   `load_full_context_data`: Загружает ВСЕ данные всех актеров (7 ключей на каждого) за один RTT.
*   `load_snapshot_data_batch`: Загружает только данные для UI (State, Meta, Loadout).
