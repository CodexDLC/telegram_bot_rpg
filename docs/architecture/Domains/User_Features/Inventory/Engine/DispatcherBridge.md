# 🌉 Inventory Dispatcher Bridge

[⬅️ Назад: Inventory Engine](../README.md)

---

## 🎯 Описание
Класс-посредник (Bridge) для взаимодействия домена Инвентаря с другими доменами через `SystemDispatcher`.
Изолирует бизнес-логику инвентаря от деталей межсервисного взаимодействия.

**Расположение:** `backend/domains/user_features/inventory/engine/dispatcher_bridge.py`

---

## 📡 Методы

### 1. `use_item_effect(char_id, item_id, item_data) -> ServiceResult | None`
Делегирует применение эффекта предмета внешнему сервису (ItemService / EffectsEngine).

*   **Input:**
    *   `char_id`: ID персонажа.
    *   `item_id`: ID предмета.
    *   `item_data`: Данные предмета (чтобы не читать их снова).
*   **Logic:**
    *   Если предмет имеет сложный эффект (телепорт, призыв), отправляет запрос в соответствующий домен.
    *   Пока реализовано как **Stub (Log only)**.
*   **Output:**
    *   `ServiceResult`: Если эффект требует смены контекста (например, телепорт в Логи).
    *   `None`: Если эффект применился локально или ничего не произошло.

### 2. `get_main_menu(char_id, context) -> MenuDTO`
Запрашивает актуальное DTO для главного меню (HUD) у домена UI/Menu.

*   **Input:**
    *   `char_id`: ID персонажа.
    *   `context`: Текущий контекст (например, "inventory_open").
*   **Logic:**
    *   Отправляет запрос в домен `Menu` (или `HUD`).
    *   Пока реализовано как **Stub (Log only)**.
*   **Output:**
    *   `MenuDTO`: Объект с данными для отрисовки нижнего меню/клавиатуры.

---

## 🔄 Интеграция

```python
class InventoryDispatcherBridge:
    def __init__(self, dispatcher: SystemDispatcher):
        self.dispatcher = dispatcher

    async def use_item_effect(self, char_id: int, item_id: int, item_data: dict) -> Any:
        # TODO: Implement real dispatch logic
        logger.info(f"Bridge: Delegating item effect for {item_id}")
        return None

    async def get_main_menu(self, char_id: int) -> Any:
        # TODO: Implement real dispatch logic
        logger.info(f"Bridge: Requesting Main Menu for {char_id}")
        return None
```
