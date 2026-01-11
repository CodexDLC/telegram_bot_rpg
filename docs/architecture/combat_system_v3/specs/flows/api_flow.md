# API Flows (Synchronous Layer)

⬅️ [Назад](../README.md) | 🏠 [Документация](../../../../README.md)

В этом документе описаны синхронные потоки данных: от запроса (внутреннего или внешнего) до записи в Redis.

---

## 1. Initialization Flow (Internal)
**Цель:** Создание новой боевой сессии.
**Trigger:** Лобби, Сценарий или Матчмейкер (через `CoreRouter`).

```mermaid
graph TD
    A[Lobby / Scenario] -->|CoreRouter.route| B(CombatEntryOrchestrator)
    B -->|Request Data| C[ContextAssembler]
    C -->|SQL Data| B
    B -->|Create Session| D[CombatLifecycleService]
    D -->|MSET| E[(Redis: Meta, Targets, Actors)]
    D -->|Link Players| F[CombatSessionService]
    D -->|Start Chaos| G[ARQ: ChaosTask]

    click B "../components/initialization.md" "CombatEntryOrchestrator Spec"
    click D "../components/lifecycle_service.md" "LifecycleService Spec"
    click F "../components/data_layer/combat_session_service.md" "SessionService Spec"
```

### Компоненты
*   [**CombatEntryOrchestrator**](../components/initialization.md) — Точка входа. Выбирает сценарий (PvE, PvP).
*   [**CombatLifecycleService**](../components/lifecycle_service.md) — Строитель сессии. Создает структуры данных.
*   [**CombatSessionService**](../components/data_layer/combat_session_service.md) — Связывает игроков с сессией.

---

## 2. Runtime Action Flow (External)
**Цель:** Игрок совершает действие (Атака, Скилл).
**Trigger:** FastAPI (Telegram Bot WebApp).

```mermaid
graph TD
    Client -->|HTTP POST| A(CombatGateway)
    A -->|Handle Action| B[CombatSessionService]
    B -->|Resolve Session| B
    B -->|Register Move| C[TurnManager]
    C -->|Validate & Atomic Push| D[(Redis: Moves)]
    C -->|Signal| E[ARQ: CollectorTask]
    B -->|Get Snapshot| F[CombatViewService]
    F -->|DTO| A
    A -->|Response| Client

    click A "../components/ingress_api.md" "CombatGateway Spec"
    click B "../components/data_layer/combat_session_service.md" "SessionService Spec"
    click C "../components/turn_manager.md" "TurnManager Spec"
    click F "../components/view_service.md" "ViewService Spec"
```

### Компоненты
*   [**CombatGateway**](../components/ingress_api.md) — API Wrapper.
*   [**CombatSessionService**](../components/data_layer/combat_session_service.md) — Фасад. Скрывает работу с сессиями.
*   [**TurnManager**](../components/turn_manager.md) — Валидатор и отправитель сигналов.
*   [**CombatViewService**](../components/view_service.md) — Презентер. Собирает DTO для ответа.

---

## 3. Runtime View Flow (External)
**Цель:** Игрок запрашивает состояние экрана (Polling / Refresh).
**Trigger:** FastAPI.

```mermaid
graph TD
    Client -->|HTTP GET| A(CombatGateway)
    A -->|Get Snapshot| B[CombatSessionService]
    B -->|Load Light Context| C[(Redis)]
    B -->|Map to DTO| D[CombatViewService]
    D -->|DashboardDTO| A
    A -->|Response| Client

    click A "../components/ingress_api.md" "CombatGateway Spec"
    click B "../components/data_layer/combat_session_service.md" "SessionService Spec"
    click D "../components/view_service.md" "ViewService Spec"
```
