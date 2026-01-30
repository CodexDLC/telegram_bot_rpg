# 🏗️ Inventory Architecture Manifest

[⬅️ Назад: Inventory Domain](./README.md)

---

## 🎯 Цель Домена
Предоставление интерфейса для управления имуществом персонажа (Инвентарь, Экипировка, Ресурсы).
Домен отвечает за **хранение, отображение и манипуляции** с предметами.

**Root Path:** `backend/domains/user_features/inventory/`

---

## 🔑 Ключевые Принципы
1.  **UI-Centric:** Бэкенд формирует готовые View DTO для клиента.
2.  **Lazy Session:** Сессия в Redis создается **только при первом обращении** (через `ContextAssembler`). Если игрок не открывает инвентарь, Redis не нагружается.
3.  **Stateless Assembler:** `ContextAssembler` используется как утилита для первичной загрузки данных из БД.
4.  **Delegation:** Сложные эффекты предметов делегируются через `DispatcherBridge`.

---

## 🧩 Компоненты Системы

### 1. [Gateway](./gateway/Gateway.md) (API Layer)
**Path:** `inventory/gateway/inventory_gateway.py`
*   Единая точка входа.
*   Маршрутизация и Response Wrapping.

### 2. [Service](./Service.md) (Domain Layer)
**Path:** `inventory/services/inventory_service.py`
*   Бизнес-логика (правила игры).
*   Сборка View DTO.

### 3. [Session Service](./Service.md) (Data Layer)
**Path:** `inventory/services/inventory_session_service.py`
*   Управление жизненным циклом сессии (Redis + ContextAssembler).
*   Lazy Loading: `Redis -> Miss -> Assembler -> Redis`.

### 4. [Resources](./data/Resources.md) (Static Data)
**Path:** `inventory/data/`
*   Тексты, конфигурации кнопок.
*   Схемы данных сессии.

### 5. [Dispatcher Bridge](./engine/DispatcherBridge.md) (Integration)
**Path:** `inventory/engine/dispatcher_bridge.py`
*   Изоляция внешних вызовов (ItemService, HUD).

---

## 🔄 Жизненный Цикл (Lazy Loading)

1.  **Request:** `GET /inventory/main`
2.  **Service:** `session_service.load_session(char_id)`
3.  **SessionService:** Проверяет Redis.
    *   **HIT:** Возвращает сессию.
    *   **MISS:**
        1.  Создает `ContextAssembler`.
        2.  Загружает данные из PostgreSQL.
        3.  Создает `InventorySessionDTO`.
        4.  Сохраняет в Redis (TTL 5 min).
        5.  Возвращает сессию.
4.  **Service:** Формирует ответ.
