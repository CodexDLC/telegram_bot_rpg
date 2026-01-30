# ⚙️ Game Menu Service

⬅️ [Back to Game Menu](../README.md)

> **Layer:** Domain Service
> **Responsibility:** Business Logic & DTO Assembly

## 1. Purpose
Основной сервис домена. Координирует сборку меню и маршрутизацию действий.
Использует `MenuSessionService` для проверки данных и `SystemDispatcher` для вызова других модулей.

## 2. Dependencies
*   `MenuSessionService`: Доступ к данным Redis и валидация.
*   `MenuResources`: Тексты кнопок и конфигурация лейаутов.
*   `SystemDispatcher`: Вызов внешних доменов (Inventory, Status).

## 3. Methods

### 3.1. `get_menu_view(char_id: int) -> GameMenuDTO`
Формирует данные для отображения меню.

*   **Logic:**
    1.  **Context:** Получает контекст через `session.get_player_context(char_id)`.
    2.  **Layout:** Определяет список кнопок на основе `context.state` (используя `MenuResources.LAYOUTS`).
    3.  **Assembly:**
        *   Заполняет HUD (HP, Energy, Name) из контекста.
        *   Формирует список кнопок, подставляя тексты из `MenuResources`.
    4.  **Return:** Готовый `GameMenuDTO`.

### 3.2. `process_menu_action(char_id: int, action: str) -> CoreResponseDTO`
Обрабатывает нажатие кнопки.

*   **Logic:**
    1.  **Validation:** Проверяет возможность перехода:
        ```python
        if not await self.session.can_perform_action(char_id, action):
            return ErrorResponse("Action not allowed in current state")
        ```
    2.  **Routing:** Определяет целевой домен по `action`.
        *   Идеально, если `action` совпадает с именем домена (например, "inventory", "status").
        *   Использует `CoreDomain` Enum для маппинга.
    3.  **Dispatch:**
        ```python
        payload = await self.dispatcher.process_action(
            domain=action, # или mapped_domain
            char_id=char_id,
            action="get_main_view" # Стандартный экшен входа
        )
        ```
    4.  **Response:** Оборачивает payload в `CoreResponseDTO` с новым хедером состояния.
