# Scenario & Quest Flow

Этот документ описывает архитектуру модуля **Scenario** (Квесты, Диалоги, Данжи).
Модуль реализует сложную логику управления состоянием и кэширования статических данных.

---

## 1. Entity Map (Карта Сущностей)

### 1.1. Bot Application Layer
*   **Orchestrator**: `ScenarioBotOrchestrator`. Презентер. Получает `ScenarioPayloadDTO` и отдает его в UI.
*   **UI Service**: `ScenarioUIService`. Строит экраны диалогов (текст, картинка, кнопки действий).
*   **Client**: `ScenarioClient`. Интерфейс API.

### 1.2. Game Core Layer
*   **Orchestrator**: `ScenarioCoreOrchestrator`. Фасад. Координирует работу компонентов.
*   **Data Manager**: `ScenarioManager`.
    *   **User Session**: Хранит прогресс игрока в Redis (`scenario_session:{char_id}`) с бэкапом в БД.
    *   **Static Cache**: Кэширует структуру квеста в Redis (`scenario:static:{quest_key}`).
*   **Logic Engine**:
    *   `ScenarioDirector`: Определяет доступные действия и следующую ноду.
    *   `ScenarioEvaluator`: Проверяет условия (Requirements) и выполняет эффекты (Rewards).
*   **Formatter**: `ScenarioFormatter`. Собирает `ScenarioPayloadDTO`.
*   **Quest Handlers**: Специализированные классы для кастомной логики квестов (награды, сложные переходы).

---

## 2. Data Flow: Initialization (Start Quest)

Запуск квеста. Система должна загрузить структуру квеста и создать сессию.

```mermaid
graph TD
    %% --- ACTORS ---
    Client["ScenarioClient"]
    CoreOrch["ScenarioCoreOrchestrator"]
    SessMgr["ScenarioManager"]
    Repo["Repository"]
    Redis["RedisService"]
    Director["ScenarioDirector"]

    %% --- FLOW ---
    Client -->|"1. initialize(quest_key)"| CoreOrch
    
    %% --- STATIC CACHE ---
    CoreOrch -->|"2. get_quest_master()"| SessMgr
    SessMgr -->|"3. Check Cache (scenario:static)"| Redis
    Redis -.->|"4. Miss"| SessMgr
    SessMgr -->|"5. Load Full Quest"| Repo
    SessMgr -->|"6. Cache Quest (TTL 1h)"| Redis
    
    %% --- SESSION CREATION ---
    CoreOrch -->|"7. register_new_session()"| SessMgr
    SessMgr -->|"8. Update Account (State=SCENARIO)"| Redis
    SessMgr -->|"9. Save Context (scenario_session)"| Redis
    SessMgr -->|"10. Backup to DB"| Repo
    
    %% --- LOGIC ---
    CoreOrch -->|"11. get_available_actions()"| Director
    
    %% --- RESPONSE ---
    CoreOrch -.->|"12. CoreResponseDTO"| Client
```

---

## 3. Data Flow: Step Execution (Player Choice)

Игрок выбирает вариант ответа.

```mermaid
graph TD
    %% --- ACTORS ---
    Client["ScenarioClient"]
    CoreOrch["ScenarioCoreOrchestrator"]
    SessMgr["ScenarioManager"]
    Director["ScenarioDirector"]
    Evaluator["ScenarioEvaluator"]

    %% --- FLOW ---
    Client -->|"1. step(action_id)"| CoreOrch
    
    %% --- LOAD ---
    CoreOrch -->|"2. load_session()"| SessMgr
    SessMgr -.->|"3. Context"| CoreOrch
    
    %% --- EXECUTE ---
    CoreOrch -->|"4. execute_step()"| Director
    Director -->|"5. check_requirements()"| Evaluator
    Director -->|"6. apply_effects()"| Evaluator
    Director -.->|"7. New Node & Context"| CoreOrch
    
    %% --- SAVE ---
    CoreOrch -->|"8. save_session_context()"| SessMgr
    
    %% --- RESPONSE ---
    CoreOrch -.->|"9. CoreResponseDTO"| Client
```

---

## 4. Data Flow: Finalization (Quest Complete)

Квест завершен. Нужно выдать награду и вернуть игрока в мир.

```mermaid
graph TD
    %% --- ACTORS ---
    CoreOrch["ScenarioCoreOrchestrator"]
    Handler["QuestHandler (Custom Logic)"]
    Router["CoreRouter"]
    SessMgr["ScenarioManager"]

    %% --- FLOW ---
    CoreOrch -->|"1. Detect 'finish_quest'"| CoreOrch
    CoreOrch -->|"2. finalize_scenario()"| CoreOrch
    
    %% --- HANDLER ---
    CoreOrch -->|"3. on_finalize()"| Handler
    Handler -->|"4. Give Rewards (XP, Items)"| Handler
    
    %% --- ROUTING ---
    Handler -->|"5. router.get_initial_view(SCENARIO/EXPLORATION)"| Router
    Router -.->|"6. CoreResponseDTO"| Handler
    
    %% --- CLEANUP ---
    CoreOrch -->|"7. clear_session()"| SessMgr
    CoreOrch -->|"8. delete_backup()"| SessMgr
    
    %% --- RETURN ---
    CoreOrch -.->|"9. CoreResponseDTO"| Client["Client"]
```

---

## 5. Key Decisions (Ключевые решения)

1.  **Static Content Caching**: Структура квеста (тексты, связи) не меняется часто. Мы загружаем весь квест из БД один раз и храним в Redis (`scenario:static:{key}`) с TTL 1 час. Это снижает нагрузку на БД при каждом шаге.
2.  **Session Resilience**: Сессия игрока живет в Redis. Если Redis падает или очищается, `ScenarioManager` умеет восстанавливать сессию из БД (`get_active_state`), где хранится бэкап.
3.  **Handler Registry**: Логика конкретных квестов (особенно финальные награды) вынесена из ядра в отдельные классы-хендлеры. Это позволяет писать уникальные скрипты для каждого квеста, не загрязняя общий движок.
