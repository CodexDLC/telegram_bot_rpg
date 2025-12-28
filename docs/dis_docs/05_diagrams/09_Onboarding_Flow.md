# Onboarding & Character Creation Flow

Этот документ описывает архитектуру модуля **Onboarding** (Создание персонажа).
Модуль следует стандарту "Тонкий Клиент" (см. `01_Architecture_Overview.md`).

---

## 1. Entity Map (Карта Сущностей)

### 1.1. Bot Application Layer
*   **Handler**: `onboarding_handler.py`. Обрабатывает колбэки и текстовый ввод (имя).
*   **Orchestrator**: `OnboardingBotOrchestrator`. Управляет флагами рендеринга (нужно ли обновлять меню).
*   **UI Service**: `OnboardingUIService`. Строит экраны (Приветствие, Ввод имени, Выбор пола).
*   **Client**: `OnboardingClient`. Интерфейс для общения с Core.

### 1.2. Game Core Layer
*   **Orchestrator**: `OnboardingCoreOrchestrator`. Фасад модуля. Управляет шагами (Step Machine).
*   **Session Manager**: `OnboardingSessionManager`. Хранит временный черновик (`OnboardingDraftDTO`) в Redis.
*   **Domain Service**: `OnboardingService`. Отвечает за создание записи в БД (`create_shell`, `finalize`).
*   **Router**: `CoreRouter`. Используется для перехода в Сценарий после завершения.

---

## 2. Data Flow: Step Transition (Смена шага)

Пример: Пользователь вводит имя "Hero".

```mermaid
graph TD
    %% --- ACTORS ---
    User((User))
    Handler["Handler<br/>(text_handler)"]
    BotOrch["OnboardingBotOrchestrator"]
    Client["OnboardingClient"]
    
    CoreOrch["OnboardingCoreOrchestrator"]
    SessMgr["OnboardingSessionManager"]
    Redis["RedisService"]

    %% --- FLOW ---
    User -->|"1. Text: 'Hero'"| Handler
    Handler -->|"2. handle_text_input()"| BotOrch
    BotOrch -->|"3. send_action('set_name', 'Hero')"| Client
    
    Client -->|"4. handle_action()"| CoreOrch
    
    %% --- LOGIC ---
    CoreOrch -->|"5. get_draft()"| SessMgr
    SessMgr -.->|"6. Draft (Step=NAME)"| CoreOrch
    
    CoreOrch -->|"7. Validate & Update Step"| CoreOrch
    CoreOrch -->|"8. update_draft(Step=GENDER)"| SessMgr
    SessMgr -->|"9. SET onboarding_draft:{uid}"| Redis
    
    %% --- RESPONSE ---
    CoreOrch -.->|"10. CoreResponseDTO<br/>(State=ONBOARDING, Payload=ViewDTO)"| Client
    Client -.->|"11. DTO"| BotOrch
    
    BotOrch -->|"12. render_view()"| BotOrch
    BotOrch -.->|"13. UnifiedViewDTO"| Handler
    Handler -->|"14. Send Message"| User
```

---

## 3. Data Flow: Finalization (Завершение)

Пользователь подтверждает создание. Происходит переход в игру.

```mermaid
graph TD
    %% --- ACTORS ---
    User((User))
    BotOrch["OnboardingBotOrchestrator"]
    Director["GameDirector"]
    Client["OnboardingClient"]
    
    CoreOrch["OnboardingCoreOrchestrator"]
    Service["OnboardingService"]
    Router["CoreRouter"]
    ScenarioOrch["ScenarioCoreOrchestrator"]

    %% --- FLOW ---
    User -->|"1. Click 'Confirm'"| BotOrch
    BotOrch -->|"2. send_action('finalize')"| Client
    Client -->|"3. handle_action()"| CoreOrch
    
    %% --- PERSISTENCE ---
    CoreOrch -->|"4. finalize_character()"| Service
    Service -->|"5. UPDATE characters DB"| Service
    
    %% --- ROUTING ---
    CoreOrch -->|"6. router.get_initial_view(SCENARIO)"| Router
    Router -->|"7. get_entry_point()"| ScenarioOrch
    ScenarioOrch -.->|"8. ScenarioPayload"| Router
    Router -.->|"9. Payload"| CoreOrch
    
    %% --- RESPONSE ---
    CoreOrch -.->|"10. CoreResponseDTO<br/>(State=SCENARIO, Payload=ScenarioPayload)"| Client
    Client -.->|"11. DTO"| BotOrch
    
    %% --- TRANSITION ---
    BotOrch -->|"12. check_and_switch_state()"| BotOrch
    BotOrch -->|"13. set_scene(SCENARIO)"| Director
    Director -->|"14. ScenarioOrchestrator.render()"| Director
```

---

## 4. Key Decisions (Ключевые решения)

1.  **Draft Storage**: Черновик хранится в Redis (`onboarding_draft:{user_id}`) и живет 24 часа. Это позволяет не мусорить в основной БД недосозданными персонажами.
2.  **Shell Creation**: При старте создается "болванка" персонажа в БД (`create_shell`), чтобы зарезервировать ID. Если пользователь бросит процесс, болванка останется (можно чистить кроном).
3.  **Core Router**: Онбординг не знает деталей Сценария. Он просто просит Роутер: "Дай мне начальный экран Сценария для этого персонажа".
