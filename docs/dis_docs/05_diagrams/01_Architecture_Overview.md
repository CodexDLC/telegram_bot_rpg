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
Отвечает за Telegram API, FSM и отрисовку (View).

```mermaid
graph TD
    Input["Telegram Update"]

    subgraph Bot_Layer ["Bot Layer"]
        Handler["Handler / Middleware"]
        Orch["Bot Orchestrator"]
        UI["UI Service (Renderer)"]
    end

    Output["NEXT: Client Layer"]

    Input --> Handler
    Handler --> Orch
    Orch -->|"Call Client"| Output
    
    Output -.->|"DTO"| Orch
    Orch -->|"Render"| UI
    UI -.->|"Message"| Handler
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