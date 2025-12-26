# Inventory System Flow

## 1. Current Architecture (AS IS)
Текущая реализация: UI-слой использует паттерн Facade, но Core-слой имеет сложные кросс-доменные зависимости и прямые запросы в БД.

```mermaid
graph TD
    %% --- СЛОИ ---
    subgraph Bot_Layer ["Bot Layer"]
        Handler["InventoryHandler"]
        Orch["InventoryBotOrchestrator"]
        
        subgraph UI_Facade ["UI Facade"]
            UI["InventoryUIService"]
            
            subgraph UI_Components ["UI Components"]
                MainMenuUI["InventoryMainMenuUI"]
                ListUI["InventoryListUI"]
                DetailsUI["InventoryDetailsUI"]
                QuickSlotUI["InventoryQuickSlotUI"]
            end
        end
    end

    subgraph Client_Layer ["Client Layer"]
        Client["InventoryClient"]
    end

    subgraph Core_Layer ["Core Layer - Cross-Domain"]
        subgraph Inv_Domain ["Inventory Domain"]
            Service["InventoryService"]
        end
        
        subgraph Stats_Domain ["Stats Domain"]
            StatsAgg["StatsAggregationService"]
        end
        
        subgraph MM_Domain ["Matchmaking Domain"]
            MM["MatchmakingService"]
        end
    end

    subgraph Data_Layer ["Data Layer"]
        InvRepo["InventoryRepo"]
        StatsRepo["CharacterStatsRepo"]
        Redis["Redis Cache"]
    end

    %% --- FLOW ---
    
    %% 1. Navigation
    Handler -->|"Open Inventory"| Orch
    Orch -->|"get_summary"| Client
    Client -->|"get_summary"| Service
    
    %% 2. Rendering (Facade Pattern)
    Orch -->|"render_main_menu"| UI
    UI -->|"Delegate"| MainMenuUI
    MainMenuUI -.->|"ViewResult"| UI
    UI -.->|"ViewResult"| Orch
    
    %% 3. Item List & Details
    Orch -->|"get_item_list"| UI
    UI -->|"Delegate"| ListUI
    
    Orch -->|"get_item_details"| UI
    UI -->|"Delegate"| DetailsUI
    
    %% 4. Actions (Equip)
    Handler -->|"Equip Action"| Orch
    Orch -->|"equip_item"| Client
    Client -->|"equip_item"| Service
    
    Service -->|"1. CRUD"| InvRepo
    Service -->|"2. Recalc Stats"| StatsAgg
    Service -->|"3. Update GS"| MM
    
    StatsAgg --> StatsRepo
    StatsAgg --> InvRepo

    %% --- Вертикальное выравнивание ---
    Orch ~~~ Client ~~~ Service ~~~ InvRepo
```

## 2. Ideal Architecture (TO BE)
Целевая архитектура: "Session-Based Inventory". `InventoryCoreOrchestrator` управляет сессией через `InventorySessionManager` и делегирует бизнес-логику в `InventoryService`.

```mermaid
graph TD
    %% --- СЛОИ ---
    subgraph Bot_Layer ["Bot Layer"]
        Handler["InventoryHandler"]
        Orch["InventoryBotOrchestrator"]
        UI["InventoryUIService"]
    end

    subgraph Client_Layer ["Client Layer"]
        Client["InventoryClient"]
    end

    subgraph Core_Layer ["Core Layer - Session Logic"]
        CoreOrch["InventoryCoreOrchestrator"]
        SessionMgr["InventorySessionManager"]
        Logic["InventoryService (Refactored)"]
    end
    
    subgraph Dispatcher_Layer ["Dispatcher Layer"]
        Dispatcher["SessionSyncDispatcher"]
    end

    subgraph Data_Layer ["Data Layer"]
        Redis["Redis - Active Session"]
        DB["PostgreSQL - Permanent Storage"]
    end

    %% --- FLOW ---
    
    %% 1. Initialization (Open Inventory)
    Handler -->|"Open Inventory"| Orch
    Orch -->|"init_session"| Client
    Client -->|"init_session"| CoreOrch
    
    %% 1.1 Session Loading
    CoreOrch -->|"load_session"| SessionMgr
    SessionMgr -->|"Check Cache"| Redis
    SessionMgr -->|"If Miss -> Load DB"| DB
    SessionMgr -.->|"InventorySessionDTO"| CoreOrch
    
    %% 1.2 View Generation
    CoreOrch -.->|"InventoryViewDTO"| Client
    
    %% 2. Fast Interaction (Equip/Move)
    Handler -->|"Equip Item"| Orch
    Orch -->|"equip_item"| Client
    Client -->|"equip_item"| CoreOrch
    
    CoreOrch -->|"get_session"| SessionMgr
    SessionMgr -.->|"InventorySessionDTO"| CoreOrch
    
    CoreOrch -->|"execute_logic(SessionDTO)"| Logic
    Logic -.->|"Modified SessionDTO"| CoreOrch
    
    CoreOrch -->|"save_session"| SessionMgr
    SessionMgr -->|"Update Cache"| Redis
    
    %% 3. Async Sync (Lazy Cleanup)
    CoreOrch -.->|"Notify Change"| Dispatcher
    Dispatcher -->|"Background: flush_session"| SessionMgr
    SessionMgr -->|"Persist to DB"| DB

    CoreOrch -.->|"Updated ViewDTO"| Client

    %% --- Вертикальное выравнивание ---
    Orch ~~~ Client ~~~ CoreOrch ~~~ SessionMgr ~~~ Redis
```

## 3. API Optimization Strategy (Single Endpoint)
Вместо десятка роутов (equip, unequip, move, drop) используем один `POST /inventory/action`.

```mermaid
graph TD
    subgraph Client_Side ["Client Side"]
        Request["POST /inventory/action"]
        Body["Body: { action: 'equip', item_id: 123 }"]
    end

    subgraph Core_API ["Core API Layer"]
        Controller["InventoryController"]
        Dispatcher["ActionDispatcher"]
    end

    subgraph Logic ["Logic Layer"]
        Orch["InventoryCoreOrchestrator"]
        SessionMgr["InventorySessionManager"]
    end

    %% --- FLOW ---
    Request --> Controller
    Body -.-> Controller
    
    Controller -->|"Validate DTO"| Dispatcher
    
    Dispatcher -->|"Switch(action)"| Dispatcher
    Dispatcher -->|"Case 'equip'"| Orch
    Dispatcher -->|"Case 'unequip'"| Orch
    Dispatcher -->|"Case 'drop'"| Orch
    
    Orch -->|"save_session"| SessionMgr
    SessionMgr -->|"Update Redis Session"| Redis["Redis"]
```