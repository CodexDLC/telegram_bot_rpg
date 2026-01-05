# Combat Turn Manager Specification (RBC v3.0)

**Role:** Gatekeeper & Timer.
**Responsibility:** Прием заявок от игроков/AI, валидация, запись в Redis и управление сигналами ARQ.

---

## 1. Core Philosophy: Double Signaling

Для обеспечения максимальной отзывчивости (Reactivity) и защиты от зависаний (Safety), каждый ход игрока генерирует **два** сигнала в ARQ.

### Signal A: The "Immediate" (Check Now)
*   **Purpose:** Мгновенная реакция.
*   **Action:** `enqueue_job('combat_collector_task', signal_type="check_immediate")`.
*   **Logic:** Коллектор просыпается сразу. Если второй игрок уже походил, бой происходит мгновенно (задержка < 0.1s).

### Signal B: The "Timeout" (Force Attack)
*   **Purpose:** Гарантия завершения хода.
*   **Action:** `enqueue_job(..., signal_type="check_timeout", _defer_until=NOW + 60s)`.
*   **Logic:** Если второй игрок так и не походил (AFK), через 60 секунд Коллектор проснется по этому сигналу. Он увидит, что пары нет, и превратит заявку в **Force Action** (односторонний удар).

---

## 2. Workflow

### A. Player Move (`register_move_request`)
1.  **Validation:** Проверка структуры Payload.
2.  **Atomic Reserve:**
    *   Использует `register_exchange_move_atomic` (Lua).
    *   Проверяет, есть ли цель в очереди `targets`.
    *   Если есть -> Удаляет цель (POP) и записывает мув.
    *   Если нет -> Ошибка (защита от спама).
3.  **Signaling:** Отправляет Immediate и Timeout сигналы.

### B. AI Batch Move (`register_moves_batch`)
1.  **Collection:** Собирает N намерений от AI Worker.
2.  **Atomic Batch:**
    *   Использует `register_moves_batch_atomic` (Lua).
    *   Для каждого мува проверяет и удаляет цель.
3.  **Signaling:**
    *   Отправляет **один** Immediate сигнал (оптимизация).
    *   Отправляет **один** Timeout сигнал на весь батч.

---

## 3. Key Features

*   **Spam Protection:** Игрок не может заявить два удара по одной цели (благодаря атомарному POP).
*   **Latency Hiding:** Игрок не ждет ответа сервера. Он отправляет мув и получает "OK". Вся магия происходит асинхронно.
*   **AFK Handling:** Таймер Force Attack заводится автоматически в момент заявки.
