# Lobby & Entry Flow

Этот документ описывает архитектуру модуля **Lobby** (Вход в игру и выбор персонажа).
Модуль следует стандарту "Тонкий Клиент" (см. `01_Architecture_Overview.md`).

---

## 1. Entity Map (Карта Сущностей)

### 1.1. Bot Application Layer
*   **Handlers**:
    *   `start_login_handler` (в `lobby.py`): Вход в лобби (кнопка "Adventure").
    *   `select_or_delete_character_handler` (в `lobby_character_selection.py`): Действия внутри (выбор, удаление, логин).
*   **Orchestrator**: `LobbyBotOrchestrator`. Управляет логикой отображения лобби.
*   **UI Service**: `LobbyService`. Строит меню выбора персонажей и статус.
*   **Client**: `LobbyClient`. Интерфейс для общения с Core.

### 1.2. Game Core Layer
*   **Orchestrator**: `LobbyCoreOrchestrator`. Фасад модуля. Управляет списком персонажей.
*   **Session Manager**: `LobbySessionManager`. Реализует паттерн Cache-Aside для списка персонажей.
*   **Data Access**:
    *   `CharacterRepository` (PostgreSQL).
    *   `RedisService` + `RedisKeys` (Redis Cache).

---

## 2. Data Flow: Initialization (Вход в Лобби)

Пользователь нажимает "Adventure". Система проверяет наличие персонажей.

```mermaid
graph TD
    %% --- ACTORS ---
    User((User))
    Handler["Handler<br/>(start_login_handler)"]
    BotOrch["LobbyBotOrchestrator"]
    Client["LobbyClient"]
    
    CoreOrch["LobbyCoreOrchestrator"]
    SessMgr["LobbySessionManager"]
    Repo["CharacterRepository"]
    Redis["RedisService"]

    %% --- FLOW ---
    User -->|"1. Click 'Adventure'"| Handler
    Handler -->|"2. process_entry_point()"| BotOrch
    BotOrch -->|"3. get_initial_lobby_state()"| Client
    
    Client -->|"4. initialize_session()"| CoreOrch
    CoreOrch -->|"5. get_characters()"| SessMgr
    
    %% --- CACHE ASIDE ---
    SessMgr -->|"6. GET lobby_session:{uid}"| Redis
    Redis -.->|"7. Miss"| SessMgr
    SessMgr -->|"8. SELECT * FROM chars"| Repo
    Repo -.->|"9. List[Character]"| SessMgr
    SessMgr -->|"10. SET lobby_session:{uid}"| Redis
    
    %% --- LOGIC ---
    SessMgr -.->|"11. Characters"| CoreOrch
    CoreOrch -->|"12. Check Count"| CoreOrch
    
    %% --- RESPONSE ---
    CoreOrch -.->|"13. CoreResponseDTO<br/>(State=LOBBY, Payload=LobbyInitDTO)"| Client
    Client -.->|"14. DTO"| BotOrch
    
    BotOrch -->|"15. render_lobby()"| BotOrch
    BotOrch -.->|"16. UnifiedViewDTO"| Handler
    Handler -->|"17. Send Message"| User
```

---

## 3. Data Flow: Enter Game (Вход в мир)

Пользователь выбирает персонажа и нажимает "Войти".

```mermaid
graph TD
    %% --- ACTORS ---
    User((User))
    Handler["Handler<br/>(select_or_delete_character_handler)"]
    BotOrch["LobbyBotOrchestrator"]
    Director["GameDirector"]
    Client["LobbyClient"]
    CoreOrch["LobbyCoreOrchestrator"]

    %% --- FLOW ---
    User -->|"1. Click 'Enter Game'"| Handler
    Handler -->|"2. handle_enter_game()"| BotOrch
    
    BotOrch -->|"3. set_char_id(123)"| Director
    BotOrch -->|"4. enter_game(char_id=123)"| Client
    
    Client -->|"5. enter_game()"| CoreOrch
    
    %% --- LOGIC ---
    CoreOrch -->|"6. Determine Target State"| CoreOrch
    CoreOrch -.->|"7. CoreResponseDTO<br/>(State=EXPLORATION)"| Client
    
    %% --- TRANSITION ---
    Client -.->|"8. DTO"| BotOrch
    BotOrch -->|"9. check_and_switch_state()"| BotOrch
    BotOrch -->|"10. set_scene(EXPLORATION)"| Director
    
    Director -->|"11. ExplorationOrchestrator.render()"| Director
```

---

## 4. Key Decisions (Ключевые решения)

1.  **Cache-Aside**: Список персонажей кэшируется в Redis (`lobby_session:{user_id}`) на 1 час. При создании/удалении персонажа кэш инвалидируется.
2.  **State Switching**: `LobbyCoreOrchestrator` сам решает, куда отправить пользователя. Если персонажей нет — он возвращает `header.current_state = ONBOARDING`. Бот просто подчиняется.
3.  **Session Context**: ID выбранного персонажа сохраняется в FSM (`GameDirector.set_char_id`) только на момент входа в игру. В самом лобби `char_id` передается в аргументах колбэка.
