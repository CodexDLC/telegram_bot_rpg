# Combat System (RBC) Flow Context Map

Этот документ описывает архитектуру и поток данных боевой системы (Reactive Burst Combat - RBC).

## 📂 Структура файлов

### 1. Handlers (Обработчики событий)
*   `apps/bot/handlers/callback/game/combat/action_handlers.py`
    *   **Роль:** Обработка основных действий боя (атака, обновление, выход).
    *   **Ключевые функции:** `submit_turn_handler` (кнопка "В атаку"), `refresh_combat_handler`, `leave_combat_handler`.
*   `apps/bot/handlers/callback/game/combat/zone_handlers.py`
    *   **Роль:** Выбор зон атаки и защиты.
    *   **Ключевые функции:** `combat_zone_toggle_handler`.
*   `apps/bot/handlers/callback/game/combat/menu_handlers.py`
    *   **Роль:** Навигация по меню боя (скиллы, предметы).
    *   **Ключевые функции:** `open_combat_menu_handler`, `switch_to_skills_handler`, `switch_to_items_handler`.
*   `apps/bot/handlers/callback/game/combat/item_handlers.py`
    *   **Роль:** Использование предметов в бою.
    *   **Ключевые функции:** `combat_item_use_handler`.
*   `apps/bot/handlers/callback/game/combat/log_handlers.py`
    *   **Роль:** Пагинация лога боя.
    *   **Ключевые функции:** `combat_log_pagination`.
*   `apps/bot/handlers/callback/game/combat/ability_handlers.py`
    *   **Роль:** Использование способностей (WIP).

### 2. UI Layer (Бот)
*   `apps/bot/ui_service/combat/combat_bot_orchestrator.py`
    *   **Роль:** Точка входа для всех действий в бою (атака, смена цели, использование предметов).
    *   **Ключевые методы:** `get_dashboard_view`, `handle_submit`.
*   `apps/bot/ui_service/combat/combat_ui_service.py`
    *   **Роль:** Рендеринг дашборда, логов и меню.
*   `apps/bot/ui_service/helpers_ui/formatters/combat_formatters.py`
    *   **Роль:** Форматирование текста (HP бары, иконки, логи).

### 3. Client Layer
*   `apps/bot/core_client/combat_rbc_client.py`
    *   **Роль:** Клиент для взаимодействия с `CombatOrchestratorRBC`.

### 4. Game Core (Ядро боя)
*   `apps/game_core/game_service/combat/combat_orchestrator_rbc.py`
    *   **Роль:** Фасад боевой системы. Инициализирует бой, регистрирует ходы, возвращает снапшоты состояния.
*   `apps/game_core/game_service/combat/combat_supervisor.py`
    *   **Роль:** Активный компонент (Loop), который следит за ходом боя, таймерами и обрабатывает обмены ударами.
*   `apps/game_core/game_service/combat/combat_service.py`
    *   **Роль:** "Мозг" расчета раунда. Выполняет математику удара, применяет эффекты, проверяет смерть.
    *   **Ключевые методы:** `process_exchange`, `use_consumable`, `switch_target`.

### 5. Mechanics (Механики)
*   `apps/game_core/game_service/combat/combat_calculator.py`: Чистая математика (урон, криты, увороты).
*   `apps/game_core/game_service/combat/ability_service.py`: Пайплайн способностей (Pre/Post calc).
*   `apps/game_core/game_service/combat/consumable_service.py`: Логика предметов.
*   `apps/game_core/game_service/combat/combat_lifecycle_service.py`: Создание сессии, сохранение результатов, начисление наград.
*   `apps/game_core/game_service/combat/combat_aggregator.py`: Сборка полного состояния персонажа (статы + эквип) перед боем.

### 6. Data & State
*   `apps/common/services/core_service/manager/combat_manager.py`: Redis-менеджер (хранение состояния боя, очередей, логов).
*   `apps/common/schemas_dto/combat_source_dto.py`: DTO (Data Transfer Objects) для обмена данными.

---

## 🔄 Поток данных: Ход игрока (Player Move)

1.  **Пользователь** нажимает "В атаку" -> `action_handlers.py` (`submit_turn_handler`).
2.  **Handler** собирает данные из FSM (зоны атаки/защиты) и вызывает `orchestrator.handle_submit`.
3.  **Bot Orchestrator** вызывает `client.register_move`.
4.  **Core Orchestrator** (`register_move`):
    *   Валидирует ход.
    *   Сохраняет ход в Redis через `CombatManager`.
    *   Убирает игрока из очереди ожидания.
5.  **Supervisor** (в фоновом цикле):
    *   Видит, что у обоих противников есть ходы (или таймер истек).
    *   Вызывает `CombatService.process_exchange`.
6.  **Combat Service**:
    *   Загружает состояния бойцов.
    *   Считает урон (`CombatCalculator`).
    *   Применяет способности (`AbilityService`).
    *   Обновляет HP/Energy.
    *   Пишет лог (`CombatLogBuilder`).
    *   Проверяет победу (`VictoryChecker`).
7.  **Bot Orchestrator** получает обновленный Snapshot и возвращает данные для обновления UI.
8.  **Handler** обновляет сообщения (дашборд и лог).
