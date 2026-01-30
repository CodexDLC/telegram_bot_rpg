# 📡 Menu Client (Telegram Bot)

⬅️ [Back to Game Menu](../../../README.md)

> **Parent:** `BaseClient`
> **Layer:** Infrastructure / Network Client

## 1. Purpose
Клиент для взаимодействия с API игрового меню. Наследуется от базового клиента, используя общую конфигурацию сессии и обработки ошибок.

## 2. Methods

### 2.1. `get_menu_view(char_id: int) -> CoreResponseDTO[GameMenuDTO]`
Запрашивает данные для отрисовки меню.

*   **Endpoint:** `GET /api/v1/game-menu/view`
*   **Return:** `CoreResponseDTO` с данными HUD и кнопок.

### 2.2. `dispatch_action(char_id: int, action: str) -> CoreResponseDTO[Any]`
Отправляет действие меню на бэкенд.

*   **Endpoint:** `POST /api/v1/game-menu/dispatch`
*   **Return:** `CoreResponseDTO`.
    *   `header.current_state`: Новый стейт (если изменился).
    *   `payload`: Данные для нового стейта (например, инвентаря).
