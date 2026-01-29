# 🛣️ Inventory API Routes

[⬅️ Назад: Inventory API](./README.md)

---

## 🎯 Концепция
API использует упрощенную REST-модель, ориентированную на игровые действия.
*   **GET**: Получение данных для отрисовки интерфейса (View).
*   **POST**: Изменение состояния предмета или персонажа (Action).
*   **DELETE**: Уничтожение предмета.

---

## 📖 Views (GET)
Запросы на получение данных. Не меняют состояние (Idempotent).

### 1. Main Menu (Кукла)
Получение сводки инвентаря: экипировка, валюта, статы.
*   **Route:** `GET /inventory/{char_id}/main`
*   **Response:** `InventoryMainViewDTO`

### 2. Bag (Сумка)
Получение списка предметов с поддержкой фильтрации и пагинации.
*   **Route:** `GET /inventory/{char_id}/bag`
*   **Query Params:**
    *   `section` (str): Раздел (equip, resource, consumable).
    *   `category` (str, optional): Подкатегория (weapon, armor...).
    *   `page` (int, default=0): Номер страницы.
*   **Response:** `InventoryBagViewDTO`

### 3. Item Details (Детали)
Получение полной информации о предмете и доступных действиях.
*   **Route:** `GET /inventory/{char_id}/items/{item_id}`
*   **Response:** `InventoryItemViewDTO`

---

## ⚡ Actions (POST)
Запросы на изменение состояния.

### 4. Equip Item
Надеть предмет на персонажа.
*   **Route:** `POST /inventory/{char_id}/items/{item_id}/equip`
*   **Body (JSON):**
    *   `slot` (str, optional): Целевой слот (если авто-выбор невозможен).
*   **Response:** `InventoryActionResultDTO`

### 5. Unequip Item
Снять предмет (вернуть в сумку).
*   **Route:** `POST /inventory/{char_id}/items/{item_id}/unequip`
*   **Response:** `InventoryActionResultDTO`

### 6. Use Item
Использовать расходник (зелье, свиток).
*   **Route:** `POST /inventory/{char_id}/items/{item_id}/use`
*   **Response:** `InventoryActionResultDTO` (содержит результат использования: "HP восстановлено").

### 7. Move / Quick Slot
Назначить предмет в быстрый слот или переместить.
*   **Route:** `POST /inventory/{char_id}/items/{item_id}/move`
*   **Body (JSON):**
    *   `target` (str): "quick_slot"
    *   `position` (int): Номер слота.
*   **Response:** `InventoryActionResultDTO`

---

## 🗑️ Destruction (DELETE)

### 8. Drop Item
Выбросить (уничтожить) предмет навсегда.
*   **Route:** `DELETE /inventory/{char_id}/items/{item_id}`
*   **Response:** `InventoryActionResultDTO`
