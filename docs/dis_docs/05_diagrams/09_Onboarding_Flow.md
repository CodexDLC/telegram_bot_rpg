# Onboarding & Character Creation Flow

## 1. Current Architecture (AS IS)
Текущая реализация: "FSM as Database". Бот хранит черновик персонажа (имя, пол) в своем FSM и собирает итоговый объект через Payload Factory.
**Проблема:** При смене клиента (например, на Web) прогресс создания потеряется, так как он привязан к FSM бота.

```mermaid
graph TD
    %% --- СЛОИ ---
    subgraph Bot_Layer ["Bot Layer (Fat Logic)"]
        Handler["OnboardingHandler"]
        Orch["OnboardingBotOrchestrator"]
        FSM["Aiogram FSM (Storage)"]
        
        subgraph UI_Components ["UI Components"]
            UI["OnboardingUIService"]
        end
        
        PayloadFactory["Payload Factory"]
    end

    subgraph Client_Layer ["Client Layer"]
        Client["OnboardingClient"]
    end

    subgraph Core_Layer ["Core Layer (Stateless)"]
        Service["OnboardingService"]
        Factory["CharacterFactory"]
    end

    subgraph Data_Layer ["Data Layer"]
        Repo["CharacterRepository"]
    end

    %% --- FLOW ---
    
    %% 1. Input Handling
    Handler -->|"Input: Name='Hero'"| Orch
    Orch -->|"Save 'Hero'"| FSM
    
    %% 2. Finalization (The Problem)
    Handler -->|"Action: Finalize"| Orch
    Orch -->|"Read All Data"| FSM
    FSM -.->|"Name, Gender..."| Orch
    Orch -->|"Construct Dict"| PayloadFactory
    PayloadFactory -.->|"DTO"| Orch
    
    %% 3. Core Call
    Orch -->|"create(DTO)"| Client
    Client -->|"create"| Service
    Service --> Factory
    Factory --> Repo

    %% --- Вертикальное выравнивание ---
    Orch ~~~ Client ~~~ Service ~~~ Factory
```

## 2. Ideal Architecture (TO BE)
Целевая архитектура: "Core Draft Session". Черновик персонажа хранится в Core (Redis). Бот просто отправляет инпуты.
**Преимущество:** Мультиплатформенность. Можно начать создавать в Telegram, продолжить в Web.

```mermaid
graph TD
    %% --- СЛОИ ---
    subgraph Bot_Layer ["Bot Layer (Thin Input)"]
        Handler["OnboardingHandler"]
        Orch["OnboardingBotOrchestrator"]
        UI["OnboardingUIService"]
    end

    subgraph Client_Layer ["Client Layer"]
        Client["OnboardingClient"]
    end

    subgraph Core_Layer ["Core Layer (Stateful Draft)"]
        CoreOrch["OnboardingCoreOrchestrator"]
        DraftMgr["DraftSessionManager"]
        Validator["InputValidator"]
        Factory["CharacterFactory"]
    end

    subgraph Data_Layer ["Data Layer"]
        Redis["Redis - Draft Session"]
        DB["PostgreSQL"]
    end

    %% --- FLOW ---
    
    %% 1. Input Handling
    Handler -->|"Input: Name='Hero'"| Orch
    Orch -->|"send_input('name', 'Hero')"| Client
    Client -->|"input"| CoreOrch
    
    %% 2. Core Logic
    CoreOrch -->|"Validate"| Validator
    CoreOrch -->|"Save to Draft"| DraftMgr
    DraftMgr -->|"Update Hash"| Redis
    
    %% 3. Finalization
    Handler -->|"Action: Finalize"| Orch
    Orch -->|"finalize()"| Client
    Client -->|"finalize()"| CoreOrch
    
    CoreOrch -->|"Get Full Draft"| DraftMgr
    DraftMgr -.->|"Draft Data"| CoreOrch
    
    CoreOrch -->|"Create"| Factory
    Factory -->|"Save"| DB
    CoreOrch -->|"Clear Draft"| DraftMgr

    %% --- Вертикальное выравнивание ---
    Orch ~~~ Client ~~~ CoreOrch ~~~ Redis
```

## 3. API Optimization Strategy (Action Dispatcher)
Как избежать создания сотен роутов. Используем один универсальный эндпоинт с полиморфным DTO.

```mermaid
graph TD
    subgraph Client_Side ["Client Side"]
        Request["POST /onboarding/action"]
        Body["Body: { action: 'set_name', value: 'Hero' }"]
    end

    subgraph Core_API ["Core API Layer"]
        Controller["OnboardingController"]
        Dispatcher["ActionDispatcher"]
    end

    subgraph Handlers ["Internal Handlers"]
        H1["SetNameHandler"]
        H2["SetGenderHandler"]
        H3["FinalizeHandler"]
    end

    %% --- FLOW ---
    Request --> Controller
    Body -.-> Controller
    
    Controller -->|"Validate Action Enum"| Dispatcher
    
    Dispatcher -->|"Switch(action)"| Dispatcher
    Dispatcher -->|"Case 'set_name'"| H1
    Dispatcher -->|"Case 'set_gender'"| H2
    Dispatcher -->|"Case 'finalize'"| H3
    
    H1 -->|"Logic"| CoreOrch["Core Orchestrator"]
```