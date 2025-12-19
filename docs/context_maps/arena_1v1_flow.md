# Arena 1v1 Flow Context Map

Этот документ описывает цепочку вызовов и файлы, участвующие в процессе работы Арены (режим 1x1), от обработки callback-запроса до взаимодействия с ядром игры.

## 📂 Структура файлов

### 1. Handlers (Обработчики событий)
*   `apps/bot/handlers/callback/game/arena/arena_1v1.py`
    *   **Роль:** Обрабатывает нажатия кнопок в меню 1x1 (вход в очередь, отмена, старт боя).
    *   **Ключевые функции:** `arena_1v1_menu_handler`, `arena_toggle_queue_handler`, `poll_for_match`, `arena_start_battle_handler`.
*   `apps/bot/handlers/callback/game/arena/arena_main.py`
    *   **Роль:** Главное меню арены и выход из сервиса.
    *   **Ключевые функции:** `arena_render_main_menu_handler`, `arena_exit_service_handler`.

### 2. UI Services (Оркестраторы интерфейса)
*   `apps/bot/ui_service/arena_ui_service/arena_bot_orchestrator.py`
    *   **Роль:** Промежуточный слой между хендлерами и клиентом ядра. Преобразует ответы ядра в готовые UI-компоненты.
    *   **Ключевые методы:** `handle_toggle_queue`, `handle_check_match`.
*   `apps/bot/ui_service/arena_ui_service/arena_ui_service.py`
    *   **Роль:** Чистый рендеринг (текст + клавиатуры). Не содержит бизнес-логики.
    *   **Ключевые методы:** `view_main_menu`, `view_mode_menu`, `view_searching_screen`, `view_match_found`.

### 3. Core Clients (Клиенты ядра)
*   `apps/bot/core_client/arena_client.py`
    *   **Роль:** Абстракция для общения с ядром. В монолите вызывает `ArenaCoreOrchestrator` напрямую.
    *   **Ключевые методы:** `toggle_queue`, `check_match`.

### 4. Game Core (Ядро игры)
*   `apps/game_core/game_service/arena/arena_orchestrator.py`
    *   **Роль:** Фасад логики арены. Маршрутизирует запросы в нужный сервис (например, `Arena1v1Service`).
    *   **Ключевые методы:** `process_toggle_queue`, `process_check_match`.
*   `apps/game_core/game_service/arena/service_1v1.py`
    *   **Роль:** Реализация логики 1x1. Управление очередью, поиск противника, создание боя (PvP или Shadow).
    *   **Ключевые методы:** `join_queue`, `check_and_match`, `create_shadow_battle`, `_create_pvp_battle`.

### 5. Managers & Services (Вспомогательные сервисы)
*   `apps/common/services/core_service/manager/arena_manager.py` (Redis: очереди, заявки)
*   `apps/game_core/game_service/matchmaking_service.py` (Расчет Gear Score)

---

## 🔄 Поток данных (Data Flow)

1.  **Пользователь** нажимает "Найти противника" -> `arena_1v1.py`
2.  **Handler** вызывает `bot_orchestrator.handle_toggle_queue`
3.  **Bot Orchestrator** вызывает `arena_client.toggle_queue`
4.  **Client** вызывает `core_orchestrator.process_toggle_queue`
5.  **Core Orchestrator** выбирает `service_1v1.join_queue`
6.  **Service 1v1**:
    *   Считает GS через `MatchmakingService`
    *   Добавляет в Redis через `ArenaManager`
    *   Возвращает статус `joined`
7.  **Цепочка возвращается** вверх, UI обновляется на "Поиск...".
8.  **Handler** запускает `poll_for_match` (цикл опроса).
