# Lobby & Entry Flow

## 1. Current Architecture (AS IS)
Текущая реализация: "Толстый Бот". Оркестратор сам управляет зависимостями и восстанавливает состояние, обращаясь к разным клиентам.

```mermaid
graph TD
    %% --- СЛОИ ---
    subgraph Bot_Layer ["Bot Layer"]
        LobbyHandler["LobbyHandler"]
        LobbyOrch["LobbyBotOrchestrator"]
        LobbyUI["LobbyService - View"]
        
        AuthOrch["AuthBotOrchestrator - Router"]
        
        subgraph Target_Orchestrators ["Target Orchestrators"]
            CombatOrch["CombatBotOrchestrator"]
            ExplOrch["ExplorationBotOrchestrator"]
            TutUI["TutorialService"]
        end
    end

    subgraph Client_Layer ["Client Layer"]
        LobbyClient["LobbyClient"]
        CombatClient["CombatRBCClient"]
        ExplClient["ExplorationClient"]
    end

    subgraph Core_Layer ["Core Layer"]
        LoginService["LoginService"]
        GameSync["GameSyncService"]
    end

    subgraph Data_Layer ["Data Layer"]
        AccountMgr["AccountManager"]
        DB["Database"]
    end

    %% --- FLOW ---
    
    %% 1. Lobby (Character Selection)
    LobbyHandler -->|"/start"| LobbyOrch
    LobbyOrch -->|"get_characters"| LobbyClient
    LobbyClient --> DB
    LobbyOrch -->|"Render List"| LobbyUI
    LobbyUI -.->|"Message"| LobbyHandler

    %% 2. Login Request
    LobbyHandler -->|"Select Char"| AuthOrch
    AuthOrch -->|"handle_login"| LoginService
    LoginService -->|"Check State"| AccountMgr
    LoginService -.->|"GameStage"| AuthOrch

    %% 3. Routing Logic (The Switch)
    AuthOrch -->|"If COMBAT"| CombatOrch
    CombatOrch -->|"Restore View"| CombatClient
    
    AuthOrch -->|"If EXPLORATION"| ExplOrch
    ExplOrch -->|"Get Location"| ExplClient
    AuthOrch -->|"Sync State"| GameSync
    
    AuthOrch -->|"If TUTORIAL"| TutUI
    
    %% 4. Final Render
    CombatOrch -.->|"Combat View"| AuthOrch
    ExplOrch -.->|"Exploration View"| AuthOrch
    TutUI -.->|"Tutorial View"| AuthOrch
    
    AuthOrch -->|"Render Target UI"| LobbyHandler

    %% --- Вертикальное выравнивание ---
    LobbyOrch ~~~ AuthOrch ~~~ LoginService ~~~ AccountMgr
```

## 2. Ideal Architecture (TO BE)
Целевая архитектура: "Тонкий Бот". Вся логика восстановления состояния инкапсулирована в Core. Бот получает полиморфный DTO и просто выбирает рендерер.

```mermaid
graph TD
    %% --- СЛОИ ---
    subgraph Bot_Layer ["Bot Layer (Thin View)"]
        Handler["LobbyHandler"]
        AuthOrch["AuthBotOrchestrator"]
        
        subgraph Renderers ["UI Renderers"]
            CombatUI["CombatUIService"]
            ExplUI["ExplorationUIService"]
            MenuUI["MenuUIService"]
        end
    end

    subgraph Client_Layer ["Client Layer"]
        SessionClient["SessionClient"]
    end

    subgraph Core_Layer ["Core Layer (Smart Logic)"]
        SessionMgr["SessionManager - Facade"]
        
        subgraph Core_Services ["Domain Services"]
            CombatSvc["CombatService"]
            WorldSvc["WorldService"]
            TutSvc["TutorialService"]
        end
    end

    %% --- FLOW ---
    
    %% 1. Request
    Handler -->|"Login"| AuthOrch
    AuthOrch -->|"restore_session"| SessionClient
    SessionClient -->|"restore_session"| SessionMgr
    
    %% 2. Core Decision (Hidden from Bot)
    SessionMgr -->|"Check State"| SessionMgr
    
    SessionMgr -->|"If Combat -> Get Snapshot"| CombatSvc
    SessionMgr -->|"If World -> Get Loc"| WorldSvc
    
    %% 3. Polymorphic Response
    CombatSvc -.->|"Data"| SessionMgr
    WorldSvc -.->|"Data"| SessionMgr
    
    SessionMgr -.->|"GameStateDTO (type=combat, data={...})"| SessionClient
    SessionClient -.->|"DTO"| AuthOrch
    
    %% 4. Dumb Rendering
    AuthOrch -->|"Switch type"| AuthOrch
    AuthOrch -->|"type=combat"| CombatUI
    AuthOrch -->|"type=world"| ExplUI
    
    CombatUI -.->|"View"| AuthOrch
    AuthOrch -->|"Message"| Handler

    %% --- Вертикальное выравнивание ---
    AuthOrch ~~~ SessionClient ~~~ SessionMgr ~~~ CombatSvc
```