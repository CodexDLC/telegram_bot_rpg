# Worker Manager (The Collector) Specification

**Role:** Matchmaker & Orchestrator.
**Responsibility:** Сбор намерений (Intents), формирование пар (Exchange), запуск Исполнителя (Executor).

---

## 1. Workflow

### A. Trigger (Signal)
Коллектор просыпается по сигналу от `TurnManager` (игрок сделал ход) или по таймеру.
Сигнал: `CollectorSignalDTO(session_id, signal_type="check_immediate" | "check_timeout" | "heartbeat")`.

### B. Snapshot Loading
Загружает **легкий слепок** данных:
*   `Meta` (кто в бою, команды).
*   `Moves` (все намерения всех игроков).
*   `Targets` (очереди целей).

### C. Logic Processing

#### 1. AI Check
Проверяет, все ли боты сделали ходы.
*   Сравнивает очередь целей бота (`targets`) с заявленными атаками (`moves.exchange`).
*   Если есть пропущенные цели -> Создает задачу `AiTurnRequestDTO` с полем `missing_targets`.
*   AI Worker получает список целей и делает `register_moves_batch`.

#### 2. Instant Harvesting (Items / Skills)
Собирает действия типа `item` и `instant`.
*   Резолвит цели (превращает "all_enemies" в список ID).
*   Записывает список целей в `move.targets`.
*   Создает **ОДИН** `CombatActionDTO` на каждое намерение (даже если целей много).

#### 3. Exchange Matchmaking (Combat)
Ищет пары для обмена ударами (PVP/PVE).
*   Игрок A бьет B. Игрок B бьет A.
*   Создает `CombatActionDTO(type="exchange", move=A, partner_move=B)`.

#### 4. Force Attack (Timeout Handling)
Если сигнал типа `check_timeout`:
*   Ищет мув, указанный в сигнале (`move_id`).
*   Если мув все еще в пуле (не нашел пару) -> Создает **Force Action**.
*   `CombatActionDTO(type="exchange", move=A, partner_move=None, is_forced=True)`.
*   Это односторонний удар по "манекену".

### D. Batch Save (Atomic Transfer)
Использует `CombatManager.transfer_intents_to_actions`:
1.  Добавляет созданные `CombatActionDTO` в очередь `q:actions`.
2.  Удаляет обработанные намерения из `moves`.
3.  Все это в одном Pipeline.

### E. Dispatch Executor
Если были созданы действия:
1.  Рассчитывает динамический `batch_size` (зависит от кол-ва участников: чем больше людей, тем меньше батч, чтобы не перегрузить воркер).
2.  Проверяет лок `sys:busy` (через `SET NX "pending"`).
3.  Если свободно -> Ставит задачу `execute_batch_task` в ARQ.

---

## 2. The "Ping-Pong" Architecture

Для обеспечения максимальной реактивности используется схема циклического вызова:

1.  **Collector:** Находит задачи -> Запускает **Executor**.
2.  **Executor:** Обрабатывает батч -> В конце **всегда** отправляет сигнал `heartbeat` **Collector**.
3.  **Collector:** Просыпается -> Проверяет AI (вдруг появились дыры в мувах после смертей) -> Проверяет остаток очереди `q:actions`.
4.  **Collector:** Если есть работа -> Снова запускает **Executor** (или AI).

Этот цикл продолжается, пока очередь не опустеет и все AI не сделают ходы.

---

## 3. Key Features

*   **Spam Protection:** Игрок не может заявить два удара по одной цели (атомарный POP при регистрации).
*   **AI Optimization:** Бот не грузит контекст, а получает цели от Коллектора. Бот регистрирует ходы пачкой.
*   **One Move = One Action:** Групповые атаки (AOE) передаются Исполнителю как один объект с списком целей.
*   **Concurrency Safety:** Коллектор не запускает нового Исполнителя, если старый еще работает (`sys:busy`).
