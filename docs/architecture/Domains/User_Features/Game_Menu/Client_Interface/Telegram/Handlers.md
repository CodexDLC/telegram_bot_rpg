# 🎮 Menu Handlers

⬅️ [Back to Game Menu](../../../README.md)

> **Layer:** Presentation (Telegram / Handlers)
> **Reference:** `game_client/bot/handlers/menu_handlers.py`

## 1. Purpose
Обработчик Callback-запросов от кнопок меню. Его задача — поймать нажатие, передать его в Оркестратор и вернуть ответ пользователю.

## 2. Handlers

### 2.1. `menu_action_handler`
*   **Trigger:** `MenuCallback` (prefix="menu")
*   **Logic:**
    1.  Извлекает `action` из callback_data.
    2.  Получает `MenuBotOrchestrator` из контейнера.
    3.  Вызывает `orchestrator.handle_menu_action(user_id, action)`.
    4.  Отвечает на callback (`call.answer()`).
    5.  Обновляет сообщение (через результат оркестратора).
