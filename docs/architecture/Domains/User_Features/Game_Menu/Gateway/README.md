# 🚪 Game Menu Gateway

⬅️ [Back to Game Menu](../README.md)

> **Layer:** Interface Adapters (Gateway)
> **Reference:** `backend/domains/user_features/game_menu/gateway/menu_gateway.py`

## 1. Responsibility (Ответственность)
Gateway служит прослойкой между HTTP API (Router) и бизнес-логикой (GameMenuService).
Его главная задача — **стандартизация ответов**. Он оборачивает любые данные от сервиса в единый транспортный конверт `CoreResponseDTO`.

## 2. Methods

### 2.1. `get_view(char_id: int) -> CoreResponseDTO`
Возвращает текущее состояние меню.

*   **Logic:**
    1.  Вызывает `GameMenuService.get_menu_view(char_id)`.
    2.  Оборачивает результат в `CoreResponseDTO`.

### 2.2. `dispatch_action(char_id: int, action: str) -> CoreResponseDTO`
Маршрутизатор действий.

*   **Logic:**
    1.  Делегирует выполнение сервису: `GameMenuService.process_menu_action(char_id, action)`.
    2.  Сервис сам возвращает готовый payload и информацию о новом стейте.
    3.  Gateway просто пробрасывает этот ответ.

## 3. Error Handling
Gateway перехватывает исключения и формирует корректный ответ для клиента.

### 3.1. Session Expired
Если сервис выбрасывает `SessionExpiredException` (сессия в Redis протухла):
*   **Action:** Gateway должен вернуть ответ, который заставит клиента уйти в Лобби.
*   **Response:**
    ```python
    return CoreResponseDTO(
        header=GameStateHeader(
            current_state=CoreDomain.LOBBY, # Force redirect
            error="session_expired"
        ),
        payload=None
    )
    ```
*   **Client Behavior:** `BaseBotOrchestrator.check_and_switch_state` увидит смену стейта на `LOBBY` и автоматически переключит сцену.

### 3.2. Other Errors
*   `ActionNotAllowed` -> `header.error = "action_not_allowed"` (стейт не меняется).
*   `DomainNotFound` -> `header.error = "internal_error"`.
