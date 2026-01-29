# 🚪 Inventory Gateway

[⬅️ Назад: Inventory Domain](../README.md)

---

## 🎯 Описание
`InventoryGateway` — это единая точка входа в домен Инвентаря со стороны API (FastAPI).
Он изолирует HTTP-слой от бизнес-логики и выполняет маршрутизацию запросов.

**Ответственность:**
1.  Прием запросов от API Routers.
2.  Валидация входных параметров (через Pydantic DTO).
3.  Вызов соответствующих методов `InventoryService`.
4.  **Response Wrapping:** Упаковка результата в `CoreResponseDTO` с правильным `GameStateHeader`.

---

## 📡 Публичные Методы (Entry Points)

Gateway предоставляет три основных метода, соответствующих HTTP-глаголам API.

### 1. `get_view(char_id, view_type, **kwargs) -> CoreResponseDTO`
Обрабатывает все **GET** запросы на получение данных.

*   **Аргументы:**
    *   `char_id` (int): ID персонажа.
    *   `view_type` (str): Тип представления (`main`, `bag`, `details`).
    *   `**kwargs`: Дополнительные фильтры (page, category, item_id).
*   **Маршрутизация:**
    *   `main` -> `service.get_main_menu(char_id)`
    *   `bag` -> `service.get_bag_view(char_id, ...)`
    *   `details` -> `service.get_item_details(char_id, item_id)`

### 2. `handle_action(char_id, action_type, **kwargs) -> CoreResponseDTO`
Обрабатывает все **POST** запросы на изменение состояния.

*   **Аргументы:**
    *   `char_id` (int): ID персонажа.
    *   `action_type` (str): Тип действия (`equip`, `unequip`, `use`, `move`).
    *   `**kwargs`: Параметры действия (item_id, slot, target).
*   **Маршрутизация:**
    *   `equip` -> `service.equip_item(...)`
    *   `unequip` -> `service.unequip_item(...)`
    *   `use` -> `service.use_item(...)` -> Может вернуть `ServiceResult` (смена стейта).
    *   `move` -> `service.move_item(...)`

### 3. `handle_delete(char_id, item_id) -> CoreResponseDTO`
Обрабатывает **DELETE** запросы.

*   **Аргументы:**
    *   `char_id` (int): ID персонажа.
    *   `item_id` (int): ID удаляемого предмета.
*   **Маршрутизация:**
    *   -> `service.drop_item(char_id, item_id)`

---

## 🔄 Response Wrapping Strategy

Gateway автоматически определяет тип ответа от сервиса и формирует заголовок.

| Тип результата от Service | GameStateHeader | Payload | Описание |
|---------------------------|-----------------|---------|----------|
| `InventoryMainViewDTO` | `INVENTORY` | `DTO` | Обычный просмотр |
| `InventoryBagViewDTO` | `INVENTORY` | `DTO` | Обычный просмотр |
| `InventoryActionResultDTO` | `INVENTORY` | `DTO` | Результат действия (успех/ошибка) |
| `ServiceResult` | `result.next_state` | `result.data` | **Смена контекста** (напр. телепорт) |
| `Exception` | `INVENTORY` | `None` | Ошибка (error="...") |

```python
def _wrap_response(self, result: Any) -> CoreResponseDTO:
    if isinstance(result, ServiceResult):
        return CoreResponseDTO(
            header=GameStateHeader(current_state=result.next_state),
            payload=result.data
        )
    
    # Default: Stay in Inventory
    return CoreResponseDTO(
        header=GameStateHeader(current_state=CoreDomain.INVENTORY),
        payload=result
    )
```
