# Worker Executor Specification

**Role:** The Muscle.
**Responsibility:** Выполнение расчетов, применение механик, сохранение результатов.

---

## 1. Workflow

### A. Trigger
Запускается Коллектором (`combat_collector_task`).
Задача: `WorkerBatchJobDTO(session_id, batch_size)`.

### B. Context Loading (Heavy)
Загружает **полный контекст** боя:
*   `Meta` (глобальные флаги).
*   `Actors` (State, Raw, Loadout, Active Abilities, XP).
*   `Queue` (список задач `q:actions`).

### C. Lock Acquisition (Optimistic)
1.  Генерирует уникальный `worker_uuid`.
2.  Пытается захватить лок `sys:busy`.
    *   Если там "pending" (от Коллектора) -> Перезаписывает на `worker_uuid`.
    *   Если там чужой UUID -> Выход (Race Condition).

### D. Batch Processing Loop
Итерирует по задачам из очереди (до `batch_size`).

Для каждой задачи (`CombatActionDTO`):
1.  **Normalization:** Превращает Action в список `Impacts` (1 или 2).
2.  **Pipeline Execution:**
    *   `Pre-Calc`: Валидация (Cost, Stun).
    *   `Calculator`: Математика (Hit, Crit, Dmg).
    *   `Mechanics`: Применение (HP, Buffs).
    *   `Post-Calc`: Реакции (Counter).
3.  **Result Accumulation:** Собирает логи и изменения стейта в памяти.

### E. Commit (Atomic Batch with Zombie Check)
Перед сохранением проверяет лок:
*   Если `sys:busy` != `worker_uuid` -> **ABORT** (Мы зомби, лок истек).
*   Если `sys:busy` == `worker_uuid` -> **COMMIT**.

Использует `CombatManager.commit_battle_results`:
1.  Применяет все изменения `State` (HINCRBY / HSET).
2.  Обновляет `Active Abilities` (JSON).
3.  Добавляет логи в `Log` (RPUSH).
4.  Удаляет обработанные задачи из `Queue` (LTRIM).
5.  Все это в одном Pipeline.

### F. Feedback Loop (Ping-Pong)
В конце работы (независимо от результата) отправляет сигнал `heartbeat` Коллектору.
Это гарантирует, что Коллектор перепроверит состояние боя (например, смерть цели) и запустит AI или новый цикл Исполнителя.

---

## 2. Key Features

*   **Optimistic Locking:** Использует `sys:busy` (Fencing Token) для защиты от параллельного запуска.
*   **Zombie Protection:** Не сохраняет данные, если потерял лок.
*   **Stateless:** Не хранит состояние между запусками.
*   **Bulk Processing:** Обрабатывает задачи пачками для снижения оверхеда на I/O.
*   **Error Isolation:** Ошибка в одной задаче не роняет весь батч (try/except внутри цикла).
