# 🚪 Inventory Gateway (API)

[⬅️ Назад: Inventory Domain](../README.md)

---

## 🎯 Описание
Точка входа в модуль Инвентаря. Реализует протокол `CoreOrchestratorProtocol`.
Этот слой имитирует будущий HTTP-клиент (FastAPI).

## 📡 Методы (Entry Points)

### 1. `get_view(char_id, view_type, **kwargs)`
Универсальный метод получения данных для отображения.

*   **Input:**
    *   `char_id` (int): ID персонажа.
    *   `view_type` (str): Тип представления (`main`, `bag`, `details`, `quick_slot_limit`).
    *   `**kwargs`: Дополнительные параметры (page, category, item_id).
*   **Output:** `InventoryViewDTO` (или dict для legacy).

**Примеры вызовов:**
*   `get_view(1, "main")` -> Главное меню.
*   `get_view(1, "bag", section="equipment", page=1)` -> Список вещей.
*   `get_view(1, "details", item_id=123)` -> Детали предмета.

---

### 2. `execute_action(char_id, action_type, **kwargs)`
Универсальный метод изменения состояния.

*   **Input:**
    *   `char_id` (int): ID персонажа.
    *   `action_type` (str): Тип действия (`equip`, `use`, `drop`, `move_quick_slot`).
    *   `**kwargs`: Параметры действия (item_id, slot, position).
*   **Output:** `tuple[bool, str]` -> `(success, message)`.

**Примеры вызовов:**
*   `execute_action(1, "equip", item_id=123, slot="main_hand")`
*   `execute_action(1, "use", item_id=456)`
*   `execute_action(1, "move_quick_slot", item_id=789, position="slot_1")`

---

## 🔗 Интеграция
Клиентская реализация находится в `apps/bot/core_client/inventory_client.py`.
Она проксирует запросы в `InventoryOrchestrator` (в будущем — в микросервис).
