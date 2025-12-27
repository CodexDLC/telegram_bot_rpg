# Lobby & Entry Flow (V2 Architecture)

## 1. The Big Picture (Ideal Flow)
Общая схема входа в игру: от команды `/start` до появления в игровом мире.

```mermaid
graph TD
    %% --- ACTORS ---
    User((User))

    %% --- BOT LAYER ---
    subgraph Bot_Layer ["Bot Layer (Presentation)"]
        StartH["Start Handler"]
        LobbyH["Lobby Handler"]
        
        CmdOrch["CommandOrchestrator"]
        LobbyOrch["LobbyOrchestrator"]
        AuthOrch["AuthOrchestrator"]
        
        Director["GameDirector"]
        Sender["ViewSender"]
    end

    %% --- CLIENT LAYER ---
    subgraph Client_Layer ["Client Layer (Bridge)"]
        AuthClient["AuthClient"]
        LobbyClient["LobbyClient"]
    end

    %% --- CORE LAYER ---
    subgraph Core_Layer ["Core Layer (Logic)"]
        UserRepo["UserRepo"]
        CharRepo["CharacterRepo"]
        SessionMgr["SessionManager"]
    end

    %% --- FLOW 1: START ---
    User -->|"/start"| StartH
    StartH -->|"handle_start()"| CmdOrch
    CmdOrch -->|"upsert_user()"| AuthClient
    AuthClient --> UserRepo
    CmdOrch -.->|"UnifiedViewDTO (Title)"| StartH
    StartH -->|"send()"| Sender

    %% --- FLOW 2: LOBBY ---
    User -->|"Click 'Adventure'"| LobbyH
    LobbyH -->|"set_scene(LOBBY)"| Director
    Director -->|"render()"| LobbyOrch
    LobbyOrch -->|"get_characters()"| LobbyClient
    LobbyClient --> CharRepo
    LobbyOrch -.->|"UnifiedViewDTO (Char List)"| Director
    Director -.->|"DTO"| LobbyH
    LobbyH -->|"send()"| Sender

    %% --- FLOW 3: LOGIN ---
    User -->|"Select Character"| LobbyH
    LobbyH -->|"handle_login()"| AuthOrch
    AuthOrch -->|"restore_session()"| SessionMgr
    SessionMgr -.->|"GameState (e.g. COMBAT)"| AuthOrch
    
    AuthOrch -->|"set_scene(COMBAT)"| Director
    Director -->|"render()"| CombatOrch["CombatOrchestrator"]
    CombatOrch -.->|"UnifiedViewDTO"| Director
    Director -.->|"DTO"| LobbyH
    LobbyH -->|"send()"| Sender
```

---

## 2. Layer Details

### 2.1. Bot Layer (Presentation)
Отвечает за обработку команд, управление сценами (Director) и отправку сообщений (Sender).

```mermaid
graph TD
    %% --- EXTERNAL ---
    Telegram((Telegram API))
    Client["External: LobbyClient"]
    Director["External: GameDirector"]

    %% --- BOT LAYER SCOPE ---
    subgraph Bot_Layer ["Bot Layer"]
        Handler["LobbyHandler"]
        Sender["ViewSender"]
        
        subgraph Orchestrator_Scope ["LobbyOrchestrator"]
            Logic["Orchestrator Logic"]
            Renderer["LobbyUIService"]
            DTO_Builder["DTO Builder"]
        end
    end
    
    %% --- DATA OBJECT ---
    DTO[("UnifiedViewDTO")]

    %% --- FLOW ---
    Telegram -->|"1. Update (Callback)"| Handler
    Handler -->|"2. handle_action()"| Logic
    
    Logic -->|"3. get_data()"| Client
    Client -.->|"4. Response (Header + Payload)"| Logic
    
    Logic --> CheckState{State Changed?}
    
    %% CASE 1: State Changed -> Call Director
    CheckState -- Yes --> CallDir["5a. director.set_scene(NewState)"]
    CallDir --> Director
    Director -.->|"6a. New UnifiedViewDTO"| Logic
    
    %% CASE 2: Same State -> Render Locally
    CheckState -- No --> Render["5b. render(Payload)"]
    Render --> Renderer
    Renderer -.->|"6b. ViewResult"| Logic
    Logic -->|"7b. Wrap"| DTO_Builder
    DTO_Builder -.->|"8b. UnifiedViewDTO"| Logic
    
    %% RETURN
    Logic -.->|"9. UnifiedViewDTO"| Handler
    
    Handler -->|"10. sender.send(DTO)"| Sender
    Sender -->|"11. Edit/Send Message"| Telegram
```

### 2.2. Client Layer (Bridge)
Связующее звено. Преобразует вызовы оркестратора в запросы к ядру (или БД для простых операций).

```mermaid
graph TD
    %% --- COMPONENTS ---
    Orchestrator["Bot Orchestrator"]
    Client["Core Client"]
    Core["Core Service / Repo"]

    %% --- FLOW ---
    Orchestrator -->|"1. get_data()"| Client
    Client -->|"2. Call Core"| Core
    Core -.->|"3. Domain Model"| Client
    Client -.->|"4. DTO"| Orchestrator
```

### 2.3. Game Core Layer (Logic)
Бизнес-логика. Для процесса входа (Login) это управление сессией и восстановление состояния.

```mermaid
graph TD
    %% --- COMPONENTS ---
    Client["Client"]
    CoreOrch["Core Orchestrator (Lobby)"]
    Repo["CharacterRepo"]
    
    %% --- FLOW ---
    Client -->|"1. get_characters(user_id)"| CoreOrch
    CoreOrch -->|"2. Fetch from DB"| Repo
    Repo -.->|"3. List[Character]"| CoreOrch
    
    CoreOrch -->|"4. Format Domain Data"| CoreOrch
    CoreOrch -.->|"5. LobbyDTO (Chars + Bio)"| Client
```