# Scenario & Quest Flow

Реализация Session-Based архитектуры для диалоговой системы.

## 1. High-Level Process (Dialogue Step)
Алгоритм обработки шага сценария.

```mermaid
graph TD
    %% --- BLOCKS ---
    Input["1. User Choice (Option ID)"]
    Context["2. Load Context (Redis)"]
    Logic["3. Logic Engine (Director)"]
    State["4. State Update (Next Node)"]
    Output["5. Render View (DTO)"]

    %% --- FLOW ---
    Input --> Context
    Context --> Logic
    
    Logic -->|"Check Conditions"| Logic
    Logic -->|"Execute Actions"| State
    
    State --> Output
    Output -.->|"New Message"| Input
```

---

## 2. Layer Details

### 2.1. Bot Layer (Presentation)
Отвечает за отрисовку диалогов и кнопок.

```mermaid
graph TD
    Input["User Callback"]

    subgraph Bot_Layer ["Bot Layer"]
        Handler["ScenarioHandler"]
        Orch["ScenarioBotOrchestrator"]
        UI["ScenarioUIService"]
    end

    Output["NEXT: Client Layer"]

    Input -->|"Click Option"| Handler
    Handler -->|"handle_action"| Orch
    Orch -->|"step_scenario"| Output
    
    Output -.->|"ScenarioViewDTO"| Orch
    Orch -->|"Render"| UI
    UI -.->|"Message"| Handler
```

### 2.2. Client Layer (The Bridge)
Изолирует Бот от логики сценариев.

```mermaid
graph TD
    Input["PREV: Bot Layer"]

    subgraph Client_Layer ["Client Layer"]
        Client["ScenarioClient"]
    end

    Output["NEXT: Game Core Layer"]

    Input -->|"step_scenario"| Client
    Client -->|"Call Core Orchestrator"| Output
    
    Output -.->|"Response DTO"| Client
    Client -.->|"Return"| Input
```

### 2.3. Game Core Layer (Business Logic)
Разделение на API (Оркестратор) и Движок (Director/Manager).

```mermaid
graph TD
    Input["PREV: Client Layer"]

    subgraph Core_Layer ["Game Core Layer"]
        
        %% Entity 1: API Interface
        subgraph Orchestrator_Entity ["1. ScenarioCoreOrchestrator (API)"]
            Orch["Orchestrator"]
            Formatter["ScenarioFormatter"]
        end
        
        %% Entity 2: Logic Engine
        subgraph Engine_Entity ["2. Scenario Engine (Logic)"]
            Director["ScenarioDirector"]
            Evaluator["ScenarioEvaluator"]
            Manager["ScenarioManager"]
        end
        
        subgraph Side_Effects ["3. Side Effects"]
            Actions["ActionExecutor"]
            Sync["SessionSyncDispatcher"]
        end
    end

    Output["NEXT: Data Layer"]

    %% --- FLOW ---
    Input -->|"step_scenario"| Orch
    
    %% 1. Load Context
    Orch -->|"load_session"| Manager
    Manager -->|"Read Redis/DB"| Output
    
    %% 2. Execute Logic
    Orch -->|"execute_step"| Director
    Director -->|"Get Node Data"| Manager
    Manager -->|"Read Global Cache"| Output
    
    Director -->|"Check Conditions"| Evaluator
    Director -->|"Execute Actions"| Actions
    Actions -->|"Give Reward"| Output
    
    %% 3. Save State
    Director -.->|"New Context"| Orch
    Orch -->|"save_session"| Manager
    Manager -->|"Write Redis"| Output
    
    %% 4. Backup (Lazy)
    Orch -.->|"Check Backup Rule"| Orch
    Orch -.->|"If needed -> sync()"| Sync
    Sync -->|"Commit to DB"| Output
    
    %% 5. Response
    Orch -->|"Build DTO"| Formatter
    Formatter -.->|"DTO"| Input
```

### 2.4. Data Layer (Storage)
Глобальный кэш для статики и сессии для пользователей.

```mermaid
graph TD
    Input["PREV: Game Core Layer"]

    subgraph Data_Layer ["Data Layer"]
        subgraph Redis_Storage ["Redis"]
            GlobalCache["Hash: Static Quest Data (1h TTL)"]
            UserSession["Hash: User Context (State)"]
        end
        
        subgraph DB_Storage ["PostgreSQL"]
            Scenarios["Table: Scenarios (JSON)"]
            Progress["Table: QuestProgress"]
        end
    end

    %% Flow
    Input -->|"Read Node"| GlobalCache
    GlobalCache -.->|"Miss -> Load"| Scenarios
    
    Input -->|"Read/Write State"| UserSession
    Input -->|"Backup State"| Progress
```

---

## 3. API Optimization Strategy
Единый роут для управления сценарием.

```mermaid
graph TD
    subgraph Client_Side ["Client Side"]
        Request["POST /scenario/action"]
        Body["Body: { action: 'step', option_id: 'opt_1' }"]
    end

    subgraph Core_API ["Core API Layer"]
        Controller["ScenarioController"]
        Dispatcher["ActionDispatcher"]
    end

    subgraph Logic ["Logic Layer"]
        Orch["ScenarioCoreOrchestrator"]
    end

    %% --- FLOW ---
    Request --> Controller
    Body -.-> Controller
    
    Controller -->|"Validate DTO"| Dispatcher
    
    Dispatcher -->|"Switch(action)"| Dispatcher
    Dispatcher -->|"Case 'start'"| Orch
    Dispatcher -->|"Case 'step'"| Orch
    Dispatcher -->|"Case 'resume'"| Orch
    
    Orch -->|"Update Redis"| Redis["Redis"]
```