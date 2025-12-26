# Exploration & Navigation Flow

Архитектура исследования мира. Координация перемещения и случайных событий.

## 1. High-Level Process (Algorithm)
Алгоритм обработки перемещения: от запроса до результата.

```mermaid
graph TD
    %% --- BLOCKS ---
    Request["1. User Request (Move To)"]
    Validation["2. Validation (Can Move?)"]
    Execution["3. Execution (Update Coords)"]
    EventRoll["4. Event Roll (Encounter?)"]
    Response["5. Response (New View)"]

    %% --- FLOW ---
    Request --> Validation
    Validation -->|"Valid"| Execution
    Validation -.->|"Invalid"| Response
    
    Execution --> EventRoll
    EventRoll -->|"Combat / Loot / Nothing"| Response
```

---

## 2. Layer Details

### 2.1. Bot Layer (Presentation)
Отвечает за отрисовку кнопок навигации и сообщений о событиях.

```mermaid
graph TD
    Input["User Callback"]

    subgraph Bot_Layer ["Bot Layer"]
        Handler["NavigationHandler"]
        Orch["ExplorationBotOrchestrator"]
        UI["ExplorationUIService"]
    end

    Output["NEXT: Client Layer"]

    Input -->|"Click Location"| Handler
    Handler -->|"move_to"| Orch
    Orch -->|"move_to"| Output
    
    Output -.->|"ExplorationViewDTO"| Orch
    Orch -->|"Render"| UI
    UI -.->|"Message"| Handler
```

### 2.2. Client Layer (The Bridge)
Изолирует Бот от логики мира.

```mermaid
graph TD
    Input["PREV: Bot Layer"]

    subgraph Client_Layer ["Client Layer"]
        Client["ExplorationClient"]
    end

    Output["NEXT: Game Core Layer"]

    Input -->|"move_to"| Client
    Client -->|"Call Core Orchestrator"| Output
    
    Output -.->|"Result DTO"| Client
    Client -.->|"Return"| Input
```

### 2.3. Game Core Layer (Business Logic)
Оркестратор координирует сервисы из разных доменов.

```mermaid
graph TD
    Input["PREV: Client Layer"]

    subgraph Core_Layer ["Game Core Layer"]
        
        %% Entity 1: Coordinator
        subgraph Orchestrator_Entity ["1. ExplorationOrchestrator (Coordinator)"]
            Orch["Orchestrator"]
        end
        
        %% Entity 2: Domain Services
        subgraph World_Domain ["2. World Domain"]
            GameWorld["GameWorldService (Meta)"]
            MoveService["MovementService (Physics)"]
        end
        
        subgraph Monster_Domain ["3. Monster Domain"]
            EncService["EncounterService (RNG)"]
        end
    end

    Output["NEXT: Data Layer"]

    %% --- FLOW ---
    Input -->|"move_to"| Orch
    
    %% 1. Validation
    Orch -->|"Get Loc Meta"| GameWorld
    GameWorld -->|"Read Redis"| Output
    
    %% 2. Movement
    Orch -->|"Execute Move"| MoveService
    MoveService -->|"Update Coords"| Output
    
    %% 3. Encounters
    Orch -->|"Check Event"| EncService
    EncService -->|"Roll Chance"| EncService
    EncService -->|"Get Mob"| Output
    
    %% 4. Response
    Orch -.->|"Result (Nav + Event)"| Input
```

### 2.4. Data Layer (Storage)
Redis хранит мир и игроков. БД хранит монстров.

```mermaid
graph TD
    Input["PREV: Game Core Layer"]

    subgraph Data_Layer ["Data Layer"]
        subgraph Redis_Storage ["Redis"]
            WorldMeta["Hash: Location Data"]
            Players["Set: Players in Loc"]
            Account["Hash: User State"]
        end
        
        subgraph DB_Storage ["PostgreSQL"]
            Monsters["Table: GeneratedClans"]
        end
    end

    %% Flow
    Input -->|"Read Meta"| WorldMeta
    Input -->|"Update Pos"| Players
    Input -->|"Update State"| Account
    
    Input -->|"Load Mob"| Monsters
```

---

## 3. API Optimization Strategy
Единый роут для действий в мире.

```mermaid
graph TD
    subgraph Client_Side ["Client Side"]
        Request["POST /exploration/action"]
        Body["Body: { action: 'move', target_id: 'forest_01' }"]
    end

    subgraph Core_API ["Core API Layer"]
        Controller["ExplorationController"]
        Dispatcher["ActionDispatcher"]
    end

    subgraph Logic ["Logic Layer"]
        Orch["ExplorationOrchestrator"]
    end

    %% --- FLOW ---
    Request --> Controller
    Body -.-> Controller
    
    Controller -->|"Validate DTO"| Dispatcher
    
    Dispatcher -->|"Switch(action)"| Dispatcher
    Dispatcher -->|"Case 'move'"| Orch
    Dispatcher -->|"Case 'look_around'"| Orch
    Dispatcher -->|"Case 'interact'"| Orch
    
    Orch -->|"Update Redis"| Redis["Redis"]
```