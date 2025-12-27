# Architecture Overview

## 1. The Big Picture (Global Flow)
Общая схема взаимодействия слоев. Каждый слой изолирован и общается только с соседями.

```mermaid
graph TD
    %% --- GLOBAL BLOCKS ---
    Bot["Bot App Layer"]
    Client["Client Bridge Layer"]
    Core["Game Core Layer"]
    Data["Data Layer (Redis/DB)"]

    %% --- CONNECTIONS ---
    Bot -->|"1. User Action"| Client
    Client -->|"2. Business Request"| Core
    Core -->|"3. CRUD Operations"| Data
    
    Data -.->|"4. Data"| Core
    Core -.->|"5. Result DTO"| Client
    Client -.->|"6. View Model"| Bot
```

---

## 2. Layer Details (Current Monolith)

### 2.1. Bot Layer (Presentation)
Отвечает за Telegram API, FSM и доставку контента. Реализует паттерн Passive View.

```mermaid
graph TD
    Input["Telegram Update"]
    Telegram["Telegram API"]

    subgraph Bot_Layer ["Bot Layer"]
        Handler["Handler (Controller)"]
        Orch["Bot Orchestrator"]
        Sender["ViewSender (Delivery)"]
    end

    Output["NEXT: Client Layer"]

    %% Flow
    Input -->|"1. Callback"| Handler
    Handler -->|"2. Process Action"| Orch
    Orch -->|"3. Call Business Logic"| Output
    
    Output -.->|"4. Domain Data"| Orch
    Orch -.->|"5. UnifiedViewDTO"| Handler
    
    Handler -->|"6. send(dto)"| Sender
    Sender -->|"7. Edit/Send Message"| Telegram
```

### 2.1.1. Bot Orchestrator Internals (UI Brain)
Оркестратор — это не просто "прокси". Это центр принятия решений UI-слоя. Он изолирует Хендлер от сложности выбора данных и форматирования.

**Алгоритм работы метода (Pipeline):**

1.  **Resolution (Выбор стратегии):**
    *   Если запрос простой — Оркестратор сам знает, какой метод Клиента вызвать.
    *   Если запрос сложный (зависит от контекста, фильтров или состояния) — Оркестратор делегирует выбор `LogicHelper`.

2.  **Data Fetching (Запрос данных):**
    *   Оркестратор вызывает `Core Client` для получения "сырых" бизнес-данных (Domain DTO).

3.  **Rendering (Визуализация):**
    *   Оркестратор вызывает `UIService` (Renderer), передавая ему бизнес-данные.
    *   `UIService` строит тексты и клавиатуры, возвращая `ViewResult`.

4.  **Packaging (Сборка):**
    *   Оркестратор упаковывает результат в `UnifiedViewDTO` (распределяет по слотам Menu/Content) и возвращает Хендлеру.

```mermaid
graph TD
    %% --- EXTERNAL ---
    Handler["External: Handler"]
    Client["External: Core Client"]

    %% --- ORCHESTRATOR INTERNAL SCOPE ---
    subgraph Orchestrator_Scope ["Bot Orchestrator (Internal Structure)"]
        Facade["Orchestrator Facade (Logic)"]
        
        subgraph Helpers ["Helpers (Optional)"]
            Strategy["Selection Strategy"]
        end
        
        subgraph Rendering ["Rendering Subsystem"]
            UIRenderer["UI Renderer (Builder)"]
            Formatter1["Text Formatter"]
            Formatter2["Keyboard Builder"]
        end
        
        Wrapper["DTO Wrapper (UnifiedViewDTO)"]
    end

    %% --- FLOW ---
    Handler -->|"1. Call Action"| Facade
    
    Facade -.->|"2. Consult (if needed)"| Strategy
    Strategy -.->|"Decision"| Facade
    
    Facade -->|"3. Request Data"| Client
    Client -->|"4. Domain Data"| Facade
    
    Facade -->|"5. Delegate Rendering"| UIRenderer
    UIRenderer -->|"Format Text"| Formatter1
    UIRenderer -->|"Build KB"| Formatter2
    UIRenderer -->|"ViewResult"| Facade
    
    Facade -->|"6. Wrap Result"| Wrapper
    Wrapper -->|"7. UnifiedViewDTO"| Handler
```

### 2.2. Client Layer (The Bridge)
Изолирует Бот от Ядра. Скрывает сложность DI и преобразует данные.

```mermaid
graph TD
    Input["PREV: Bot Layer"]

    subgraph Client_Layer ["Client Layer"]
        Client["Core Client"]
        DTO["DTO Converter"]
    end

    Output["NEXT: Game Core Layer"]

    Input -->|"Method Call"| Client
    Client -->|"Prepare Args"| DTO
    Client -->|"Call Core"| Output
    
    Output -.->|"Result"| Client
    Client -.->|"Return"| Input
```

### 2.3. Game Core Layer (Business Logic)
Чистая бизнес-логика. Правила игры, расчеты, управление состоянием.

```mermaid
graph TD
    Input["PREV: Client Layer"]

    subgraph Core_Layer ["Game Core Layer"]
        CoreOrch["Core Orchestrator"]
        Service["Domain Service"]
        Logic["Logic / Calculator"]
        Manager["Manager / Repo"]
    end

    Output["NEXT: Data Layer"]

    Input --> CoreOrch
    CoreOrch --> Service
    Service --> Logic
    Service --> Manager
    Manager -->|"Read/Write"| Output
    
    Output -.->|"Data"| Manager
    Service -.->|"Result"| CoreOrch
    CoreOrch -.->|"Response DTO"| Input
```

---

## 3. Target Architecture (HTTP API Microservices)
Целевая архитектура при разделении на микросервисы (Bot + Core API).

```mermaid
graph TD
    %% --- BOT SIDE ---
    subgraph Bot_App ["Bot Application"]
        Handler["Handler"]
        BotOrch["Bot Orchestrator"]
        HttpClient["HTTP Client (httpx)"]
    end

    %% --- NETWORK ---
    Network["HTTP / JSON"]

    %% --- CORE SIDE ---
    subgraph Core_App ["Core Application (FastAPI)"]
        Router["API Router (Controller)"]
        CoreOrch["Core Orchestrator"]
        Logic["Business Logic"]
    end

    %% --- FLOW ---
    Handler -->|"Action"| BotOrch
    BotOrch -->|"call_api()"| HttpClient
    HttpClient -->|"POST /domain/action"| Network
    
    Network -->|"Request"| Router
    Router -->|"Validate DTO"| Router
    Router -->|"handle_action()"| CoreOrch
    CoreOrch -->|"Execute"| Logic
    
    Logic -.->|"Result"| CoreOrch
    CoreOrch -.->|"Response DTO"| Router
    Router -.->|"JSON Response"| Network
    
    Network -.->|"Response"| HttpClient
    HttpClient -.->|"DTO"| BotOrch
```