# Onboarding & Character Creation Flow

## Architecture Overview

Мы используем вертикальную архитектуру с разделением на слои.
Данные черновика (Draft) хранятся в Redis (Core Layer) и не гоняются туда-сюда целиком, только необходимые DTO для отображения.

---

## 1. Bot Layer (UI & Management)
**Responsibility:** Обработка ввода, управление UI, делегирование логики.

```mermaid
graph TD
    subgraph Bot_Layer ["Bot Layer"]
        User((User))
        Handler["OnboardingHandler"]
        Orch["OnboardingBotOrchestrator"]
        Director["GameDirector"]
        Sender["ViewSender"]
        
        User -->|"Text/Callback"| Handler
        Handler -->|"handle_input()"| Orch
        
        Orch -->|"Check Header"| Orch
        Orch -.->|"Switch Scene"| Director
        
        Orch -->|"Return ViewDTO"| Handler
        Handler -->|"send(ViewDTO)"| Sender
        Sender -->|"Update UI"| User
    end
```

---

## 2. Client Layer (Transport)
**Responsibility:** Транспорт данных между Bot и Core. Превращает вызовы методов в запросы (DTO).

```mermaid
graph TD
    subgraph Client_Layer ["Client Layer"]
        BotOrch["Bot Orchestrator"]
        Client["OnboardingClient"]
        CoreOrch["Core Orchestrator"]
        
        BotOrch -->|"send_action(action, value)"| Client
        Client -->|"CoreResponseDTO"| BotOrch
        
        Client -->|"initialize_session()"| CoreOrch
        Client -->|"process_action()"| CoreOrch
    end
```

---

## 3. Core Layer (Business Logic & State)
**Responsibility:** Валидация, управление шагами, хранение черновика, финализация.

```mermaid
graph TD
    subgraph Core_Layer ["Core Layer"]
        CoreOrch["OnboardingCoreOrchestrator"]
        SessMgr["OnboardingSessionManager"]
        Repo["CharacterRepository"]
        
        CoreOrch -->|"get/update draft"| SessMgr
        CoreOrch -->|"create_character"| Repo
        
        subgraph Logic ["Business Logic"]
            StepLogic["Step Transition (Name -> Gender -> ...)"]
            Validator["Input Validator"]
        end
        
        CoreOrch --> StepLogic
        CoreOrch --> Validator
    end
```

---

## 4. Data Layer (Storage)
**Responsibility:** Хранение данных.

```mermaid
graph TD
    subgraph Data_Layer ["Data Layer"]
        SessMgr["SessionManager"]
        Redis[("Redis (Draft Session)")]
        Repo["Repository"]
        DB[("PostgreSQL (Final Data)")]
        
        SessMgr -->|"SET onboarding_draft:{char_id}"| Redis
        SessMgr -->|"GET onboarding_draft:{char_id}"| Redis
        
        Repo -->|"INSERT characters"| DB
    end
```

---

## Data Flow Example: "Set Name"

1.  **Bot:** Юзер пишет "Hero". Хендлер передает это в Оркестратор.
2.  **Client:** Оркестратор вызывает `client.send_action(char_id, "set_name", "Hero")`.
3.  **Core:**
    *   `CoreOrchestrator` получает запрос.
    *   Валидирует ("Hero" - ок).
    *   `SessionManager` обновляет Redis: `name="Hero"`.
    *   `CoreOrchestrator` переключает шаг на `GENDER`.
    *   Возвращает `CoreResponseDTO` (Header=ONBOARDING, Payload=ViewDTO(step=GENDER)).
4.  **Bot:** Оркестратор получает ответ, формирует UI выбора пола и отправляет через `ViewSender`.
