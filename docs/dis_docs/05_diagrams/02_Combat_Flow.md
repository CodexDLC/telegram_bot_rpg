# Combat System Flow (RBC)

Этот документ описывает архитектуру модуля **Combat** (Боевая система).
Модуль реализует пошаговый бой (Round Based Combat) с механикой непрерывного обмена (Continuous Exchange) и асинхронной обработкой ходов.

---

## 1. Entity Map (Карта Сущностей)

### 1.1. Bot Application Layer
*   **Handlers**: `apps/bot/handlers/callback/game/combat/combat_handlers.py`
    *   `on_combat_control`: Управление боем (Зоны, Скиллы, Предметы). Обновляет Content (Нижнее сообщение).
    *   `on_combat_menu`: Управление меню (Лог, Настройки). Обновляет Menu (Верхнее сообщение).
    *   `on_combat_flow`: Жизненный цикл (Submit, Leave). Запускает анимацию ожидания (Polling).
*   **Orchestrator**: `CombatBotOrchestrator`.
    *   Управляет локальным стейтом (FSM) через `CombatStateManager`.
    *   Управляет анимацией ожидания (через `UIAnimationService`).
    *   Формирует `UnifiedViewDTO`.
*   **UI Services**:
    *   `CombatContentUI`: Рендерит Дашборд, Сетку, Меню скиллов/предметов.
    *   `CombatMenuUI`: Рендерит Лог боя.
    *   `CombatFlowUI`: Рендерит экраны ожидания и результатов.

### 1.2. Game Core Layer
*   **Orchestrator**: `CombatOrchestratorRBC`. Фасад (API).
    *   `register_move()`: Принимает ход и кладет в Redis.
    *   `get_dashboard_snapshot()`: Читает состояние из Redis.
*   **Session Manager**: `CombatManager`.
    *   Хранит маппинг `char_id -> session_id`.
    *   Загружает `CombatSessionContainerDTO` из Redis.
*   **Worker**: `CombatSupervisor`. Фоновый процесс.
    *   Сканирует активные сессии.
    *   Запускает расчет при совпадении условий (Match/Timeout).
*   **Engine**: `CombatService`. Чистая логика расчета урона.

---

## 2. Data Flow: Combat Controls (Управление Боем)

Игрок выбирает зоны атаки/защиты или использует предмет.

```mermaid
graph TD
    %% --- ACTORS ---
    User((User))
    Handler["combat_handlers.py"]
    BotOrch["CombatBotOrchestrator"]
    StateManager["CombatStateManager (FSM)"]
    Client["CombatRBCClient"]
    CoreOrch["CombatOrchestratorRBC"]

    %% --- FLOW ---
    User -->|"1. Click 'toggle_zone'"| Handler
    Handler -->|"2. handle_control_event()"| BotOrch
    
    %% --- LOCAL STATE ---
    BotOrch -->|"3. Update Selection"| StateManager
    StateManager -->|"4. Save to FSM"| StateManager
    
    %% --- SNAPSHOT (Always Fresh) ---
    BotOrch -->|"5. get_snapshot()"| Client
    Client -->|"6. get_snapshot()"| CoreOrch
    CoreOrch -.->|"7. DashboardDTO"| Client
    
    %% --- RENDER ---
    Client -.->|"8. DTO"| BotOrch
    BotOrch -->|"9. Render Content (Grid + HP)"| BotOrch
    BotOrch -.->|"10. UnifiedViewDTO"| Handler
    Handler -->|"11. Edit Content Message"| User
```

---

## 3. Continuous Exchange Pipeline (Asynchronous)

Система разделена на два независимых процесса, связанных через Redis.

### A. Input Flow (Client Side)
Игрок делает ход. Задача системы — принять заявку и вернуть управление (или статус ожидания).

```mermaid
graph TD
    %% --- ACTORS ---
    User((User))
    BotOrch["BotOrchestrator"]
    CoreAPI["CombatOrchestratorRBC (API)"]
    Redis[("Redis (Moves & Queue)")]

    %% --- FLOW ---
    User -->|"1. Submit Move"| BotOrch
    BotOrch -->|"2. Register Move"| CoreAPI
    
    CoreAPI -->|"3. Save Bullet (MoveDTO)"| Redis
    CoreAPI -->|"4. Pop Target from Queue"| Redis
    
    Redis -.->|"5. Queue State"| CoreAPI
    
    CoreAPI -->|"6. Decision"| Decision{Queue > 0?}
    
    Decision -->|"Yes: Return New Target"| BotOrch
    BotOrch -->|"Render Next Enemy"| User
    
    Decision -->|"No: Return Status=Waiting"| BotOrch
    BotOrch -->|"Start Polling Animation"| User
```

### B. Processing Flow (Server Side)
Фоновый процесс обрабатывает заявки. Бот здесь не участвует.

```mermaid
graph TD
    %% --- ACTORS ---
    Supervisor["Supervisor (Worker)"]
    Service["CombatService (Logic)"]
    Redis[("Redis (Moves & Queue)")]

    %% --- LOOP ---
    Supervisor -->|"1. Scan Active Sessions"| Redis
    Redis -.->|"2. Moves & Timers"| Supervisor
    
    Supervisor -->|"3. Trigger Condition?"| Check{Match or Timeout?}
    
    Check -->|"Yes"| Service
    Check -->|"No"| Supervisor
    
    %% --- CALCULATION ---
    Service -->|"4. Process Exchange"| Service
    Service -->|"5. Update HP/Stats"| Redis
    
    %% --- ROTATION ---
    Service -->|"6. Return Actors to Queue"| Redis
```

### Детализация этапов:

1.  **Player Phase (UI)**:
    *   Игрок видит цель (первую из очереди).
    *   Делает ход (`Submit`).
    *   Пуля улетает в Redis, цель удаляется из начала очереди.
    *   Если в очереди есть **еще** враги — игрок сразу получает следующего.
    *   Если очередь пуста — игрок переходит в режим ожидания (`Waiting`).

2.  **Engine Phase (Supervisor)**:
    *   Воркер сканирует пули.
    *   **Trigger**: Запускает расчет, если:
        *   Есть встречная пуля (Враг тоже ударил).
        *   ИЛИ вышел таймер (Враг AFK).

3.  **Calculation Phase**:
    *   `CombatService` считает урон.
    *   **Rotation**: Возвращает живых бойцов в конец очередей друг друга.

4.  **Return Phase**:
    *   Очередь игрока пополняется (враг вернулся).
    *   Бот видит это через поллинг и разблокирует UI.

---

## 4. Key Decisions (Ключевые решения)

1.  **Asynchronous Processing**: Ввод хода и его расчет развязаны. Бот не ждет расчета, он ждет изменения состояния в Redis (через поллинг).
2.  **Continuous Flow**: Игрок может сделать несколько ходов подряд (по разным целям), если они есть в очереди. Блокировка UI (`Waiting`) наступает только когда очередь пуста.
3.  **Snapshot-Based UI**: При любом действии мы запрашиваем свежий снапшот. Это гарантирует, что игрок видит актуальное HP, даже если расчет произошел в фоне.
4.  **UI Layout**: Разделение на Menu (Лог) и Content (Дашборд) позволяет обновлять их независимо.
