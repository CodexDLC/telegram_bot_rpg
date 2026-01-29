# 📱 Telegram Client Interface (Inventory)

[⬅️ Назад: Client Interface](../README.md)

---

## 🎯 Описание
Реализация интерфейса инвентаря для Telegram бота (Aiogram).
Этот слой является **"Тонким клиентом" (Thin Client)**. Его задача — отобразить данные, полученные от Backend, и отправить команды пользователя.

**Принципы:**
1.  **Backend-Driven Data:** Бэкенд присылает **структурированные данные (DTO)**, а не готовый HTML.
2.  **Client-Side Presentation:** Клиентский слой (`UIService` + `Formatters`) отвечает за превращение данных в красивый HTML-текст.
3.  **Facade UI Service:** Для сложных доменов, как Инвентарь, основной `UIService` действует как фасад, делегируя рендеринг специализированным UI-компонентам.

---

## 🏗️ Структура Кода (Client)

### 1. Feature Root
**Путь:** `src/game_client/telegram_bot/features/inventory/`

### 2. System (UI Logic)
**Путь:** `features/inventory/system/`
*   `inventory_bot_orchestrator.py`: Координатор.
*   `inventory_ui_service.py`: **Фасад**, который вызывает компоненты.

### 3. UI Components
**Путь:** `features/inventory/components/`
*   `doll_ui.py`: Рендерит экран "Кукла".
*   `bag_ui.py`: Рендерит список предметов.
*   `details_ui.py`: Рендерит карточку предмета.

### 4. Resources
**Путь:** `features/inventory/resources/`
*   `keyboards/`: Фабрики `CallbackData`.
*   `formatters/`: Классы со статическими методами для генерации HTML из DTO.

---

## 🛠️ Implementation Details (Specs)

### InventoryUIService (Facade)
```python
class InventoryUIService(BaseUIService):
    def __init__(self, ...):
        self.doll_ui = DollUI(...)
        self.bag_ui = BagUI(...)
        self.details_ui = DetailsUI(...)

    def render(self, payload: InventoryUIPayloadDTO) -> ViewResultDTO:
        # Делегирование на основе экрана
        if payload.screen == "main":
            return self.doll_ui.render(payload)
        elif payload.screen == "bag":
            return self.bag_ui.render(payload)
        elif payload.screen == "details":
            return self.details_ui.render(payload)
        
        raise ValueError(f"Unknown screen: {payload.screen}")
```

### DetailsUI (Component Example)
```python
class DetailsUI:
    def render(self, payload: InventoryUIPayloadDTO) -> ViewResultDTO:
        # 1. Генерация HTML через Formatter
        text = InventoryFormatter.format_details(payload.context)
        
        # 2. Генерация клавиатуры
        kb = self._build_keyboard(payload.buttons)
            
        return ViewResultDTO(text=text, kb=kb)
```
