# 🧱 Client Base Classes (Shared Kernel)

[⬅️ Назад: Architecture](../README.md)

---

## 🎯 Описание
Базовые классы для Telegram-клиента, обеспечивающие унификацию обработки ответов от бэкенда.

**Расположение:** `src/game_client/telegram_bot/base/`

---

## 🎻 BaseBotOrchestrator

**Файл:** `base_orchestrator.py`

Базовый класс для всех оркестраторов доменов (Inventory, Exploration, Combat).
Обеспечивает стандартную обработку `CoreResponseDTO`.

### Методы

#### `process_response(self, response: CoreResponseDTO | CoreCompositeResponseDTO) -> UnifiedViewDTO`
Главный метод обработки ответа API.

**Логика:**
1.  **Error Check:** Если `response.header.error` -> Возвращает Alert/Error View.
2.  **Redirect Check:** Если `response.header.current_state != expected_state` -> Вызывает `director.process_transition`.
3.  **Composite Check:** Если `response` имеет поле `menu_payload` (или тип Composite) -> Вызывает `_process_composite`.
4.  **Standard Render:** Иначе вызывает `render_content(response.payload)`.

#### `_process_composite(self, response: CoreCompositeResponseDTO) -> UnifiedViewDTO`
Обработка составного ответа (Контент + Меню).

**Логика:**
1.  **Menu:** Вызывает `self.container.menu_ui_service.render(response.menu_payload)`.
2.  **Content:** Вызывает `self.render_content(response.payload)`.
3.  **Result:** Возвращает `UnifiedViewDTO(content=..., menu=...)`.

#### `render_content(self, payload: Any) -> ViewResultDTO`
**Abstract Method.** Должен быть реализован в наследниках.
Отвечает за рендеринг специфичного для домена контента.

---

## 🎨 BaseUIService

**Файл:** `base_ui_service.py`

Базовый класс для UI сервисов.

### Методы
*   `render(payload: Any) -> ViewResultDTO`: Абстрактный метод.
