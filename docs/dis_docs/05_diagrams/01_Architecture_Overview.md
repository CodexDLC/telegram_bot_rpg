# Architecture Overview: Entity Map & Data Flow

Этот документ описывает структуру проекта и потоки данных.

---

## 1. General Architecture (Общая Схема)
Глобальные потоки данных между слоями.

```mermaid
graph TD
    %% --- BLOCKS ---
    Bot["1. Bot Application Layer"]
    Gateway["2. Gateway Layer"]
    Core["3. Game Core Layer"]
    Data["4. Data Access Layer"]

    %% --- DOWNSTREAM (Request) ---
    Bot -->|"1. Action Request"| Gateway
    Gateway -->|"2. Routed Request"| Core
    Core -->|"3. CRUD Operations"| Data

    %% --- UPSTREAM (Response) ---
    Data -.->|"4. Domain Entities"| Core
    Core -.->|"5. CoreResponseDTO"| Gateway
    Gateway -.->|"6. CoreResponseDTO"| Bot
```

---

## 2. Layer Details (Детализация Слоев)

### 2.1. Bot Application Layer (Presentation)
Слой представления.

```mermaid
graph TD
    %% --- INPUT ---
    User((User)) -->|"1. Input"| Handler["Handler"]
    
    %% --- LOGIC ---
    subgraph Logic_Scope ["Logic & Transport"]
        direction TB
        Handler -->|"2. handle()"| BotOrch["BotOrchestrator"]
        BotOrch <-->|"3. Request/Response"| Gateway["Gateway Layer"]
    end

    %% --- RENDERING ---
    subgraph Render_Scope ["Rendering Engine"]
        direction TB
        BotOrch -->|"4. Check State"| Decision{Changed?}
        
        Decision -->|Yes| Director["GameDirector"]
        Director -->|"5a. Switch & Render"| UIService["UIService"]
        
        Decision -->|"No: 5b. Update View"| UIService
    end

    %% --- OUTPUT ---
    UIService -.->|"6. ViewDTO"| BotOrch
    BotOrch -.->|"7. UnifiedViewDTO"| Handler
    Handler -->|"8. send()"| Sender["ViewSender"]
    Sender -->|"9. Update UI"| User
```

### 2.2. Gateway Layer (Transport Bridge)
Слой транспорта.

#### Phase 1: Current Implementation (Monolith)
Клиент выступает абстрактной прослойкой.

```mermaid
graph TD
    %% --- TOP: BOT ---
    subgraph Bot_Layer ["Bot Layer"]
        BotOrch["BotOrchestrator"]
    end

    %% --- MIDDLE: CLIENT (The Bridge) ---
    subgraph Client_Interface ["Client Interface (Abstract Bridge)"]
        style Client_Interface fill:#eee,stroke:#999,stroke-dasharray: 5 5
        ApiClient["ApiClient"]
    end

    %% --- BOTTOM: CORE ---
    subgraph Core_Layer ["Core Layer"]
        CoreRouter["CoreRouter"]
        CoreOrch["CoreOrchestrator"]
    end

    %% --- FLOW ---
    BotOrch -->|"1. await client.method()"| ApiClient
    
    ApiClient -->|"2. Direct Call"| CoreRouter
    CoreRouter -->|"3. Route"| CoreOrch
    
    CoreOrch -.->|"4. Return DTO"| CoreRouter
    CoreRouter -.->|"5. Return DTO"| ApiClient
    
    ApiClient -.->|"6. Return DTO"| BotOrch
```

#### Phase 2: Target Architecture (Microservices)
Сетевое взаимодействие через HTTP.

```mermaid
graph LR
    %% --- CLIENT SIDE ---
    subgraph Bot_Side ["Bot Service"]
        direction TB
        ApiClient["ApiClient"] -->|"1. Call"| HttpClient["HTTP Client"]
    end

    %% --- NETWORK ---
    HttpClient <-->|"2. JSON / HTTP"| Network((Internet))

    %% --- SERVER SIDE ---
    subgraph Core_Side ["Core Service"]
        direction TB
        Network <-->|"3. Request"| FastAPI["FastAPI Router"]
        FastAPI <-->|"4. Call Logic"| CoreOrch["CoreOrchestrator"]
    end
```

### 2.3. Game Core Layer (Business Logic)
Слой бизнес-логики.

#### A. Structure (Компоненты и Зависимости)
Кто кого содержит и использует.

```mermaid
graph TD
    subgraph Core_Module ["Domain Module (e.g. Combat)"]
        CoreOrch["CoreOrchestrator<br/>(Facade)"]
        
        subgraph Data_Mgmt ["Data Management"]
            SessMgr["SessionManager"]
            RedisMgr["SpecificRedisManager<br/>(Singleton from Common)"]
        end
        
        Service["DomainService<br/>(Pure Logic)"]
    end
    
    CoreRouter["CoreRouter<br/>(Mediator)"]
    Repo["Repository<br/>(DB)"]

    %% Dependencies
    CoreOrch --> SessMgr
    CoreOrch --> Service
    CoreOrch -.-> CoreRouter
    
    SessMgr --> RedisMgr
    SessMgr --> Repo
```

#### B. Execution Flow (Поток выполнения)
Как обрабатывается один запрос.

```mermaid
graph TD
    %% --- ACTORS ---
    Gateway["Gateway"]
    CoreOrch["CoreOrchestrator"]
    SessMgr["SessionManager"]
    Service["DomainService"]
    
    %% --- 1. LOAD ---
    Gateway -->|"1. Action"| CoreOrch
    CoreOrch -->|"2. get_session()"| SessMgr
    SessMgr <-->|"3. Load (Redis/DB)"| Data[("Data Layer")]
    SessMgr -.->|"4. Session Object"| CoreOrch
    
    %% --- 2. EXECUTE ---
    CoreOrch -->|"5. Execute Logic"| Service
    Service -.->|"6. Result"| CoreOrch
    
    %% --- 3. SAVE ---
    CoreOrch -->|"7. save_session()"| SessMgr
    SessMgr -->|"8. Persist (Redis/DB)"| Data
    
    %% --- 4. RETURN ---
    CoreOrch -.->|"9. CoreResponseDTO"| Gateway
```

### 2.4. Data Access Layer (Persistence)
Слой данных.

```mermaid
graph TD
    subgraph Data_Layer ["Data Access Layer"]
        Repo["Repository"]
        Redis["RedisService"]
    end

    DB[("PostgreSQL")]
    Cache[("Redis")]

    Repo <-->|"SQL / Rows"| DB
    Redis <-->|"Get / Set"| Cache
```