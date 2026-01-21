# 🛠️ Task: Migration to Session-Based Inventory

> **Status:** Planned
> **Priority:** High
> **Goal:** Переход от CRUD-модели (прямые запросы в БД) к Session-Based модели (Redis Cache).

## 1. Проблема (Current State)
*   **Direct DB Access:** `InventoryService` обращается к PostgreSQL при каждой операции (equip, move, get).
*   **Performance:** Пересчет статов и проверка слотов (`get_capacity`) нагружают базу.
*   **Consistency:** Нет единого транзакционного контекста для серии операций.

## 2. Целевая Архитектура (Target State)

### 2.1. Компоненты
1.  **InventoryGateway (API):** Единая точка входа. Принимает команды (`EquipRequest`, `MoveRequest`).
2.  **InventoryOrchestrator (Session):**
    *   `load_session(char_id)`: Загружает инвентарь из БД в Redis (`inventory:session:{uuid}`).
    *   `save_session(char_id)`: Сбрасывает изменения из Redis в БД (асинхронно или при выходе).
3.  **InventoryEngine (Logic):**
    *   Работает **только** с DTO в памяти (`InventorySessionDTO`).
    *   Не знает про базу данных.
    *   Выполняет проверки: "Влезет ли предмет?", "Можно ли надеть?".

### 2.2. Взаимодействие с Item System
*   Инвентарь хранит только `item_id` (instance) и `template_id`.
*   Данные о предмете (название, статы) запрашиваются через `ItemGateway` (кэшируемый).

## 3. План Миграции

### Step 1: Session Manager Implementation
*   Создать `InventorySessionManager` в слое Orchestrator.
*   Реализовать сериализацию/десериализацию `InventorySessionDTO` <-> Redis JSON.

### Step 2: Engine Refactoring
*   Переписать методы `equip_item`, `move_item` в `InventoryService` (или новом `InventoryEngine`), чтобы они принимали `SessionDTO` и возвращали измененный `SessionDTO`.
*   Убрать SQL-запросы из логики.

### Step 3: Gateway Integration
*   Настроить `InventoryGateway` на использование Оркестратора.
*   Обеспечить вызов `load_session` перед началом работы с инвентарем (Middleware или явный вызов).

## 4. Задействованные файлы
*   `apps/game_core/modules/inventory/inventory_orchestrator.py`
*   `apps/game_core/modules/inventory/inventory_service.py`
*   `apps/game_core/modules/inventory/logic/bag_logic.py`
