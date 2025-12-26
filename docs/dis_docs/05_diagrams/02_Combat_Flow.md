# Combat System Flow (RBC)

Эталонная реализация Session-Based архитектуры.

## 1. High-Level Process (RBC Loop)
Алгоритм боевого раунда: от заявки до результата.

```mermaid
graph TD
    %% --- BLOCKS ---
    Input["1. Player Move (Bullet)"]
    Queue["2. Queue (Redis)"]
    Engine["3. Engine (Supervisor)"]
    Calc["4. Calculation (Damage/Effects)"]
    Output["5. State Update (Snapshot)"]

    %% --- FLOW ---
    Input -->|"Push"| Queue
    Queue -->|"Poll"| Engine
    
    Engine -->|"Match Pair"| Calc
    Calc -->|"Apply Rules"| Output
    
    Output -.->|"Notify UI"| Input
```

---

## 2. Layer Details

### 2.1. Bot Layer (Presentation)
Отвечает за обработку кнопок и отрисовку экрана боя.

```mermaid
graph TD
    Input["User Callback"]

    subgraph Bot_Layer ["Bot Layer"]
        Handler["ActionHandler"]
        Orch["CombatBotOrchestrator"]
        UI["CombatUIService"]
        Formatter["CombatFormatter"]
    end

    Output["NEXT: Client Layer"]

    Input -->|"Click"| Handler
    Handler -->|"handle_submit"| Orch
    Orch -->|"register_move"| Output
    
    Output -.->|"CombatViewDTO"| Orch
    Orch -->|"Render"| UI
    UI -->|"Format Text"| Formatter
    UI -.->|"Message"| Handler
```

### 2.2. Client Layer (The Bridge)
Изолирует Бот от сложной логики RBC.

```mermaid
graph TD
    Input["PREV: Bot Layer"]

    subgraph Client_Layer ["Client Layer"]
        Client["CombatRBCClient"]
    end

    Output["NEXT: Game Core Layer"]

    Input -->|"register_move"| Client
    Client -->|"Call Core Orchestrator"| Output
    
    Output -.->|"DashboardDTO"| Client
    Client -.->|"Return"| Input
```

### 2.3. Game Core Layer (Business Logic)
Разделение на синхронный API (Оркестратор) и фоновый Актер (Супервизор).

```mermaid
graph TD
    Input["PREV: Client Layer"]

    subgraph Core_Layer ["Game Core Layer"]
        
        %% Entity 1: API Interface
        subgraph Orchestrator_Entity ["1. CombatOrchestratorRBC (API)"]
            Orch["Orchestrator"]
            Lifecycle["LifecycleService"]
        end
        
        %% Entity 2: Background Engine
        subgraph Supervisor_Entity ["2. CombatSupervisor (Background Actor)"]
            Supervisor["Supervisor Loop"]
            AI["CombatAIService"]
            Service["CombatService"]
            Calc["CombatCalculator"]
        end
    end

    Output["NEXT: Data Layer"]

    %% --- FLOW 1: Orchestrator (Read/Write) ---
    Input -->|"register_move / get_snapshot"| Orch
    
    Orch -->|"Save Move (Bullet)"| Output
    Orch -->|"Read State (Snapshot)"| Output
    Orch -.->|"Ensure Supervisor Running"| Supervisor
    
    Orch -.->|"Return DTO"| Input
    
    %% --- FLOW 2: Supervisor (Processing) ---
    Supervisor -->|"Poll Redis (While True)"| Output
    
    %% Logic Details
    Supervisor -->|"1. Check Timeouts"| Supervisor
    Supervisor -->|"2. Check Mutual Moves"| Supervisor
    Supervisor -->|"3. Generate AI Moves"| AI
    
    %% Execution
    Supervisor -->|"4. Execute Exchange"| Service
    Service -->|"Calculate Hit"| Calc
    Service -->|"Apply Effects"| Service
    Service -->|"Update Redis State"| Output
    Service -->|"Push Logs"| Output
    
    %% Finish
    Service -->|"If Dead -> Check Win"| Lifecycle
    Lifecycle -->|"Save Stats to DB"| Output
```

### 2.4. Data Layer (Storage)
Redis хранит активную сессию (быстро). БД хранит результаты (надежно).

```mermaid
graph TD
    Input["PREV: Game Core Layer"]

    subgraph Data_Layer ["Data Layer"]
        subgraph Redis_Session ["Redis (Active Session)"]
            Meta["Hash: Meta"]
            Actors["Hash: Actors State"]
            Moves["Hash: Moves (Bullets)"]
            Queues["List: Exchange Queues"]
        end
        
        subgraph DB_Storage ["PostgreSQL (Persistence)"]
            Stats["Table: CharacterStats"]
            History["Table: CombatHistory"]
        end
    end

    Input -->|"Read/Write"| Redis_Session
    Input -->|"Commit Result"| DB_Storage
```

---

## 3. API Optimization Strategy
Единый роут для всех боевых действий.

```mermaid
graph TD
    subgraph Client_Side ["Client Side"]
        Request["POST /combat/action"]
        Body["Body: { action: 'move', target_id: 1, zones: [...] }"]
    end

    subgraph Core_API ["Core API Layer"]
        Controller["CombatController"]
        Dispatcher["ActionDispatcher"]
    end

    subgraph Logic ["Logic Layer"]
        Orch["CombatCoreOrchestrator"]
    end

    %% --- FLOW ---
    Request --> Controller
    Body -.-> Controller
    
    Controller -->|"Validate DTO"| Dispatcher
    
    Dispatcher -->|"Switch(action)"| Dispatcher
    Dispatcher -->|"Case 'move'"| Orch
    Dispatcher -->|"Case 'use_item'"| Orch
    Dispatcher -->|"Case 'surrender'"| Orch
    
    Orch -->|"Update Redis"| Redis["Redis"]
```