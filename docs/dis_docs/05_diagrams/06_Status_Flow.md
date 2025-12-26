# Status & Character Menu Flow

## 1. Current Architecture (AS IS)
Текущая реализация: "Агрегатор в Боте". Оркестратор и Сервис знают слишком много о связях между доменами.

```mermaid
graph TD
    %% --- СЛОИ ---
    subgraph Bot_Layer ["Bot Layer - UI Logic"]
        Handler["StatusHandler"]
        Orch["StatusBotOrchestrator"]
        
        subgraph UI_Services ["Tab UI Services"]
            BioUI["CharacterMenuUIService - Bio"]
            SkillUI["CharacterSkillStatusService - Skills"]
            ModUI["CharacterModifierUIService - Mods"]
        end
        
        Formatters["Formatters - Text Builders"]
    end

    subgraph Client_Layer ["Client Layer"]
        Client["StatusClient"]
    end

    subgraph Core_Layer ["Core Layer - Data Aggregation"]
        Service["StatusService"]
        StatsAgg["StatsAggregationService"]
        InvService["InventoryService"]
    end

    subgraph Data_Layer ["Data Layer"]
        StatsRepo["CharacterStatsRepo"]
        Redis["Redis Cache"]
    end

    %% --- FLOW ---
    
    %% 1. Request Routing
    Handler -->|"Open Tab key"| Orch
    Orch -->|"get_full_data"| Client
    Client -->|"get_full_data"| Service
    
    %% 2. Core Data Fetching
    Service -->|"Fetch Stats"| StatsRepo
    Service -->|"Fetch Items"| InvService
    Service -->|"Calc Mods"| StatsAgg
    
    Service -.->|"FullCharacterDataDTO"| Client
    Client -.->|"DTO"| Orch

    %% 3. UI Routing & Rendering
    Orch -->|"If tab == bio"| BioUI
    Orch -->|"If tab == skills"| SkillUI
    Orch -->|"If tab == modifiers"| ModUI
    
    %% 4. Skill Drill-Down Logic
    SkillUI -->|"Level: Root Group Detail"| SkillUI
    SkillUI -->|"Format Text"| Formatters
    
    %% 5. Response
    BioUI -.->|"ViewResult"| Orch
    SkillUI -.->|"ViewResult"| Orch
    ModUI -.->|"ViewResult"| Orch
    
    Orch -->|"Render Message"| Handler

    %% --- Вертикальное выравнивание ---
    Orch ~~~ Client ~~~ Service ~~~ StatsRepo
```

## 2. Ideal Architecture (TO BE)
Целевая архитектура: "Session-Based Status". CoreOrchestrator управляет сессией и делегирует логику сервису.

```mermaid
graph TD
    %% --- СЛОИ ---
    subgraph Bot_Layer ["Bot Layer"]
        Handler["StatusHandler"]
        Orch["StatusBotOrchestrator"]
        UI["StatusUIService"]
    end

    subgraph Client_Layer ["Client Layer"]
        Client["StatusClient"]
    end

    subgraph Core_Layer ["Core Layer - Session Logic"]
        CoreOrch["StatusCoreOrchestrator"]
        Logic["StatusLogicService"]
    end
    
    subgraph Dispatcher_Layer ["Dispatcher Layer"]
        Dispatcher["SessionSyncDispatcher"]
        Registry["Orchestrator Registry"]
    end

    subgraph Data_Layer ["Data Layer"]
        Redis["Redis - Active Session"]
        DB["PostgreSQL - Permanent Storage"]
    end

    %% --- FLOW ---
    
    %% 1. Initialization (Open Profile)
    Handler -->|"Open Profile"| Orch
    Orch -->|"init_session"| Client
    Client -->|"init_session"| CoreOrch
    
    %% 1.1 Lazy Cleanup
    CoreOrch -->|"Async Task: sync()"| Dispatcher
    Dispatcher -->|"Check Orphan Sessions"| Redis
    Dispatcher -->|"If Orphan Found -> Backup"| Registry
    Registry -->|"backup_session()"| CoreOrch
    CoreOrch -->|"Commit Changes (if any)"| DB
    
    %% 1.2 Session Start (Heavy Calc)
    CoreOrch -->|"Check Cache"| Redis
    CoreOrch -->|"If Miss -> Aggregate All"| DB
    CoreOrch -->|"Cache Full Profile"| Redis
    
    CoreOrch -.->|"StatusViewDTO"| Client
    
    %% 2. Fast Interaction (Switch Tabs)
    Handler -->|"Switch Tab"| Orch
    Orch -->|"get_tab_view"| Client
    Client -->|"get_tab_view"| CoreOrch
    
    CoreOrch -->|"Read Session"| Redis
    CoreOrch -.->|"Tab Data"| Client
    
    %% 3. Actions (e.g. Upgrade Skill)
    Handler -->|"Upgrade Skill"| Orch
    Orch -->|"upgrade_skill"| Client
    Client -->|"upgrade"| CoreOrch
    
    CoreOrch -->|"Get Session"| Redis
    CoreOrch -->|"execute_logic"| Logic
    Logic -.->|"Modified State"| CoreOrch
    CoreOrch -->|"Update Session"| Redis
    
    CoreOrch -.->|"Updated View"| Client

    %% --- Вертикальное выравнивание ---
    Orch ~~~ Client ~~~ CoreOrch ~~~ Redis
```

## 3. API Optimization Strategy (Action Dispatcher)
Объединяем все действия с персонажем (прокачка, сброс, смена титула) в один роут.

```mermaid
graph TD
    subgraph Client_Side ["Client Side"]
        Request["POST /status/action"]
        Body["Body: { action: 'upgrade_skill', skill_id: 'fireball' }"]
    end

    subgraph Core_API ["Core API Layer"]
        Controller["StatusController"]
        Dispatcher["ActionDispatcher"]
    end

    subgraph Logic ["Logic Layer"]
        Orch["StatusCoreOrchestrator"]
    end

    %% --- FLOW ---
    Request --> Controller
    Body -.-> Controller
    
    Controller -->|"Validate DTO"| Dispatcher
    
    Dispatcher -->|"Switch(action)"| Dispatcher
    Dispatcher -->|"Case 'upgrade_skill'"| Orch
    Dispatcher -->|"Case 'reset_stats'"| Orch
    Dispatcher -->|"Case 'set_title'"| Orch
    
    Orch -->|"Update Redis Session"| Redis["Redis"]
```