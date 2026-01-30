# ✍️ Inventory Handlers Specification

[⬅️ Назад: Telegram Client](./README.md)

---

## 🎯 Концепция
Вместо множества хендлеров, мы используем два, разделенных по **намерению пользователя**, что зеркалит REST-подход бэкенда:
1.  **View Handler:** Обрабатывает навигацию (GET-запросы).
2.  **Action Handler:** Обрабатывает действия с предметами (POST/DELETE-запросы).

---

## 🏭 Callback-фабрики
**Расположение:** `features/inventory/resources/keyboards/callbacks.py`

### 1. `InventoryViewCB` (prefix="inv_v")
Для навигации и запроса данных.

```python
class InventoryViewCB(CallbackData, prefix="inv_v"):
    target: InventoryViewTarget  # Enum: main, bag, details
    payload: str | None = None   # JSON-строка с параметрами (page, category, item_id)
```

### 2. `InventoryActionCB` (prefix="inv_a")
Для выполнения действий.

```python
class InventoryActionCB(CallbackData, prefix="inv_a"):
    action: InventoryActionType  # Enum: equip, use, drop
    item_id: int
    payload: str | None = None   # Доп. параметры (slot, position)
```

---

## 🚦 Хендлеры

### 1. View Handler (Навигация)
**Файл:** `features/inventory/handlers/inventory_view_handler.py`

**Ответственность:** Обработка `InventoryViewCB`. Запрашивает у бэкенда данные для отрисовки экранов.

```python
@router.callback_query(InventoryViewCB.filter())
async def handle_view_navigation(
    call: CallbackQuery, 
    callback_data: InventoryViewCB, 
    state: FSMContext,
    container: Container
):
    # 1. Сборка контекста
    director = GameDirector(container, state, call.from_user.id)
    orchestrator = container.inventory_orchestrator()
    orchestrator.set_director(director)

    # 2. Вызов логики (GET-like)
    view_dto = await orchestrator.handle_view_request(callback_data)

    # 3. Рендеринг
    await ViewSender(call).send(view_dto)
```

### 2. Action Handler (Действия)
**Файл:** `features/inventory/handlers/inventory_action_handler.py`

**Ответственность:** Обработка `InventoryActionCB`. Выполняет действия с предметами (Equip, Use, **Drop/Delete**).

```python
@router.callback_query(InventoryActionCB.filter())
async def handle_inventory_action(
    call: CallbackQuery, 
    callback_data: InventoryActionCB, 
    state: FSMContext,
    container: Container
):
    # 1. Сборка контекста
    director = GameDirector(container, state, call.from_user.id)
    orchestrator = container.inventory_orchestrator()
    orchestrator.set_director(director)

    # 2. Вызов логики (POST/DELETE-like)
    view_dto = await orchestrator.handle_action_request(callback_data)

    # 3. Рендеринг (обычно это обновленный экран)
    await ViewSender(call).send(view_dto)
```

---

## 🏷️ Новые Enums
**Расположение:** `common/schemas/inventory/enums.py`

```python
from enum import StrEnum

class InventoryViewTarget(StrEnum):
    MAIN = "main"
    BAG = "bag"
    DETAILS = "details"

class InventoryActionType(StrEnum):
    EQUIP = "equip"
    UNEQUIP = "unequip"
    USE = "use"
    MOVE = "move"
    DROP = "drop"  # Это наш DELETE
```
