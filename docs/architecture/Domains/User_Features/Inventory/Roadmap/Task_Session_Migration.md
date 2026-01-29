# 🛠️ Task: Migration to Session-Based Inventory & Composite UI

> **Status:** 🟡 In Progress
> **Priority:** Critical
> **Goal:** Переход на Session-Based архитектуру (RedisJSON) и внедрение Composite Response для поддержки двухпанельного UI (Content + Menu).

---

## 1. Контекст и Проблемы
*   **Legacy:** Текущая (или планируемая ранее) реализация подразумевала прямой CRUD в БД или отсутствие четкого разделения слоев.
*   **UI Limitation:** Базовый оркестратор не умеет обрабатывать сложные ответы, содержащие данные и для контента, и для меню одновременно.
*   **Performance:** Необходим кэш сессии, чтобы не нагружать БД при каждом открытии инвентаря.

---

## 2. Целевая Архитектура (Target State)

### 2.1. Data Layer (RedisJSON)
*   **Storage:** Инвентарь хранится как единый JSON-документ в Redis.
*   **Key:** `ac:{char_id}:inventory`
*   **Structure:** `InventorySessionDTO` (Items, Equipment, Wallet, Stats).
*   **Persistence:**
    *   **Read:** Redis -> (Miss) -> ContextAssembler (DB) -> Redis.
    *   **Write:** Redis -> Dirty Flag -> Async Worker (Future) / Explicit Save.

### 2.2. API Layer (Composite Response)
*   **DTO:** `CoreCompositeResponseDTO[T, M]`
    *   `header`: GameStateHeader
    *   `payload`: T (Content DTO, например `InventoryBagViewDTO`)
    *   `menu_payload`: M (Menu DTO, например `HUDMenuDTO`)
*   **Gateway:** Оборачивает ответы сервиса в CompositeDTO.

### 2.3. Client Layer (Thin Client)
*   **BaseBotOrchestrator:** Получает метод `process_response`, который умеет разделять CompositeDTO на Content и Menu.
*   **InventoryOrchestrator:** Делегирует рендеринг `InventoryUIService`.

---

## 3. План Реализации (Implementation Plan)

### Phase 1: Shared Kernel (Infrastructure)
*   [x] **DTO Update:** Добавить `CoreCompositeResponseDTO` в `common/schemas/response.py`.
*   [x] **Base Orchestrator:**
    *   Реализовать `process_response(response)`.
    *   Добавить логику обработки CompositeDTO (вызов рендера контента и меню).
    *   Добавить абстрактный метод `render_content`.

### Phase 2: Inventory Domain (Data & Logic)
*   [x] **Domain DTOs:** Создать схемы `InventorySessionDTO`, `InventoryItemDTO`, `InventoryViewDTO` (Bag, Doll, Details).
*   [ ] **Resources:** Реализовать `InventoryResources` (тексты, кнопки).
*   [ ] **Session Manager:** Реализовать `InventorySessionManager` (Redis operations, Lazy Load stub).
*   [ ] **Enricher:** Реализовать `InventoryEnricher` (превращение ID -> Name/Icon).
*   [ ] **Service:** Реализовать бизнес-логику (`get_view`, `equip`, `unequip`, `move`) работающую с сессией.
*   [ ] **Gateway:** Реализовать `InventoryGateway` с возвратом `CoreCompositeResponseDTO`.

### Phase 3: Client Implementation
*   [ ] **UI Components:** Создать `DollUI`, `BagUI`, `DetailsUI`.
*   [ ] **UI Service:** Реализовать `InventoryUIService` (Facade).
*   [ ] **Orchestrator:** Реализовать `InventoryBotOrchestrator` (наследник Base, реализация `render_content`).
*   [ ] **Handlers:** Создать `InventoryViewHandler` и `InventoryActionHandler`.

---

## 4. Зависимости
*   `ContextAssembler` (будет использоваться как Stub/Mock на первом этапе, либо вызов существующего кода).
*   `MenuService` (для получения данных HUD).
