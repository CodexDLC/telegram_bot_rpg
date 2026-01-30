# 🔌 Game Menu API

⬅️ [Back to Game Menu](../README.md)

> **Base URL:** `/api/v1/game-menu`

## 1. Get Menu View
Получение данных для отрисовки "Верхнего меню" (HUD + Кнопки).
Используется при инициализации сессии или обновлении экрана.

*   **Method:** `GET`
*   **Path:** `/view`
*   **Query Params:**
    *   `char_id`: int

### Response
*   **Schema:** `CoreResponseDTO[GameMenuDTO]`
*   **DTO Location:** `src/common/schemas/game_menu.py`

#### Example Payload (JSON)
> ⚠️ **Note:** Структура `hud` зависит от реальных данных в Redis (Status/Vitals). Ниже приведен пример.

```json
{
  "header": {
    "current_state": "EXPLORATION",
    "transaction_id": "uuid..."
  },
  "payload": {
    "hud": {
      "hp": 100,
      "max_hp": 100,
      "energy": 50,
      "max_energy": 50,
      "char_name": "Hero",
      "buffs": ["🔥", "🛡️"]
    },
    "buttons": [
      {"id": "inventory", "text": "📦 Inventory", "is_active": true},
      {"id": "status", "text": "ℹ️ Status", "is_active": true},
      {"id": "map", "text": "🗺️ Map", "is_active": true}
    ]
  }
}
```

---

## 2. Dispatch Action
Обработка нажатия кнопки в меню.
Бэкенд определяет логику перехода и возвращает данные для нового экрана.

*   **Method:** `POST`
*   **Path:** `/dispatch`

### Request
*   **Schema:** `MenuActionRequest`

```json
{
  "char_id": 123,
  "action_id": "inventory" // ID кнопки из списка buttons
}
```

### Response
*   **Schema:** `CoreResponseDTO[T]` (Generic Payload)
*   **Description:** Возвращает payload, соответствующий новому стейту (`header.current_state`).
*   **Note:** На данном этапе (до рефакторинга всех доменов) используется `Any` или `Dict` в качестве payload. В будущем здесь будет `Union[InventoryDTO, StatusDTO, ...]`.

#### Example (Success - Switch to Inventory)
```json
{
  "header": {
    "current_state": "INVENTORY", // Бот переключает FSM на Inventory
    "previous_state": "EXPLORATION"
  },
  "payload": {
    // Здесь возвращается полная структура InventoryDTO (items, slots, etc.)
    // См. документацию домена Inventory
  }
}
```

#### Example (Success - Switch to Status)
```json
{
  "header": {
    "current_state": "STATUS",
    "previous_state": "EXPLORATION"
  },
  "payload": {
    // Здесь возвращается полная структура StatusDTO (stats, bio, equipment)
    // См. документацию домена Status
  }
}
```

---

## 3. Dependency Injection (DI)

### 3.1. Backend Dependencies
Регистрация сервисов и гейтвеев происходит в `backend/dependencies/features/game_menu.py`.
Подключение к главному контейнеру — в `backend/dependencies/base.py`.

*   **Services:** `MenuSessionService`, `GameMenuService`
*   **Gateway:** `GameMenuGateway`

### 3.2. System Dispatcher Integration
Домен использует `Dispatcher` для вызова других модулей (Internal Call).

*   **Dependency:** `backend.dependencies.internal.dispatcher` (уже существует).
*   **Usage:** `GameMenuService` вызывает `dispatcher.dispatch(target_domain, ...)` для получения данных целевого экрана.
