# Технический долг: Лобби и Вход

## Текущий статус vs Целевая архитектура
**Текущее состояние**: "Толстый Бот". Оркестратор Бота решает, какой UI показать, основываясь на флагах, и управляет потоком.
**Цель**: "Тонкий Бот". Core `SessionManager` определяет состояние и возвращает полиморфный DTO.

## Проблемы (Gaps)
1.  **Размытие логики**: Логика "Куда должен попасть пользователь?" разделена между `AuthBotOrchestrator` и `LoginService`.
2.  **Отсутствие `SessionManager`**: В Core нет центрального компонента, который знает "Пользователь X находится в Бою Y" или "Пользователь X в Исследовании Z".

## План действий
1.  **Создать `SessionManager` (Фасад)**:
    *   Метод: `get_current_state(char_id) -> GameStateDTO`.
    *   Логика:
        *   Проверить `CombatManager` (Redis) -> если активен -> вернуть `GameState.COMBAT`.
        *   Проверить `AccountManager` -> получить `location_id` -> вернуть `GameState.EXPLORATION`.
2.  **Рефакторинг `AuthBotOrchestrator`**:
    *   Вызвать `SessionManager.get_current_state()`.
    *   Переключиться по типу результата и делегировать соответствующему Рендереру (CombatUI, ExplorationUI).

## Задействованные файлы
*   `apps/game_core/game_service/lobby/lobby_orchestrator.py` (Оркестратор Core)
*   `apps/game_core/game_service/auth/login_service.py` (Логика входа)
*   `apps/bot/ui_service/auth/auth_bot_orchestrator.py` (Оркестратор бота, требует упрощения)
*   `apps/bot/handlers/callback/login/login_handler.py` (Хендлер входа)
*   `apps/bot/core_client/lobby_client.py` (Клиент)
