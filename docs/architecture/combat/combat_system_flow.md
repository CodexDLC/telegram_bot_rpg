# Combat System (RBC) Flow Context Map

Этот документ описывает архитектуру и поток данных боевой системы (Reactive Burst Combat - RBC).
Актуально для версии: **New Architecture (UnifiedViewDTO + ViewSender)**.

## 📂 Структура файлов (Bot Layer)

### 1. Handlers (Обработчики событий)
*   `apps/bot/handlers/callback/game/combat/combat_handlers.py`
    *   **Роль:** Единая точка входа для всех боевых колбэков.
    *   **Хендлеры:**
        *   `on_combat_control`: Обработка кликов по сетке, навигации, выбора предметов/скиллов.
        *   `on_combat_menu`: Обработка действий меню (лог, инфо, настройки).
        *   `on_combat_flow`: Обработка глобальных действий (Submit, Leave). Запускает анимацию ожидания.

### 2. Orchestrator (Бизнес-логика UI)
*   `apps/bot/ui_service/combat/combat_bot_orchestrator.py`
    *   **Роль:** Управляет состоянием UI, вызывает Core Client, формирует UnifiedViewDTO.
    *   **Ключевые методы:**
        *   `handle_control_event`: Обновляет FSM (Draft) -> Запрашивает Snapshot -> Рендерит.
        *   `handle_flow_event`: Отправляет ход (Submit) -> Возвращает статус (Waiting/Active).
        *   `check_combat_status`: Поллинг статуса боя (для анимации).
        *   `render`: Вход в бой (начальная отрисовка).

### 3. State Management (FSM)
*   `apps/bot/ui_service/combat/helpers/combat_state_manager.py`
    *   **Роль:** Управляет временным состоянием выбора (Draft) в FSM.
    *   **Данные:** Зоны атаки/защиты, выбранный скилл.
    *   **Методы:** `toggle_zone`, `set_ability`, `get_move_data`.

### 4. UI Services (Рендеринг)
*   `apps/bot/ui_service/combat/services/content_ui.py`: Рендер нижнего сообщения (Дашборд, Сетка, Меню скиллов/предметов).
*   `apps/bot/ui_service/combat/services/menu_ui.py`: Рендер верхнего сообщения (Лог боя, Инфо о цели).
*   `apps/bot/ui_service/combat/services/flow_ui.py`: Рендер экранов потока (Ожидание, Результаты, Смерть).
*   `apps/bot/ui_service/combat/formatters/combat_formatters.py`: Форматирование текста.

### 5. Client Layer (Связь с Core)
*   `apps/bot/core_client/combat_rbc_client.py`
    *   **Роль:** Тонкий прокси к `CombatOrchestratorRBC`.
    *   **Методы:** `get_snapshot`, `register_move`, `perform_action`, `get_data`.

---

## 🔄 Поток данных (Data Flow)

### 1. Выбор действий (Draft Phase)
1.  **User** кликает по зоне (например, "Голова") -> `c_ctrl:zone:head`.
2.  **Handler** (`on_combat_control`) вызывает `orchestrator.handle_control_event`.
3.  **Orchestrator**:
    *   Вызывает `manager.toggle_zone` (обновляет FSM).
    *   Вызывает `client.get_snapshot` (получает актуальное состояние боя).
    *   Вызывает `content_ui.render_content` (рисует дашборд с обновленной сеткой).
4.  **Handler** отправляет обновленное сообщение через `ViewSender`.

### 2. Отправка хода (Submit Phase)
1.  **User** нажимает "В атаку" -> `c_flow:submit`.
2.  **Handler** (`on_combat_flow`) вызывает `orchestrator.handle_flow_event`.
3.  **Orchestrator**:
    *   Собирает `move_data` из `manager`.
    *   Вызывает `client.register_move`.
    *   Возвращает `UnifiedViewDTO` и флаг `is_waiting`.
4.  **Handler**:
    *   Если `is_waiting` -> Запускает `UIAnimationService.start_combat_polling`.
    *   **Animation Service**:
        *   Крутит цикл (каждые 2 сек).
        *   Вызывает `orchestrator.check_combat_status`.
        *   Обновляет сообщение ("Ожидание...").
        *   Если статус сменился на `active` -> показывает результат.

### 3. Использование предмета (Instant Action)
1.  **User** выбирает предмет -> `c_ctrl:pick:item:123`.
2.  **Orchestrator**:
    *   Вызывает `client.perform_action("use_item")`.
    *   Core применяет предмет мгновенно.
    *   Orchestrator запрашивает обновленный снапшот и логи.
    *   Рендерит Main Dashboard.

---

## 🏗 Core Layer (Ожидаемый интерфейс)

Bot ожидает от Core (`CombatOrchestratorRBC`) следующие методы (через `CoreResponseDTO`):

1.  `get_snapshot_wrapped(char_id) -> CoreResponseDTO[CombatDashboardDTO]`
    *   Возвращает полное состояние боя для UI.
2.  `register_move_wrapped(char_id, target_id, move_data) -> CoreResponseDTO[CombatDashboardDTO]`
    *   Регистрирует ход. Если `target_id=0`, Core выбирает цель из очереди.
3.  `perform_action(char_id, action_type, payload) -> CoreResponseDTO[CombatActionResultDTO]`
    *   Мгновенные действия (use_item, flee).
4.  `get_data(char_id, data_type, params) -> CoreResponseDTO[Any]`
    *   Получение вспомогательных данных (logs, info).

### DTO Structures

*   **CombatDashboardDTO**:
    *   `player`: ActorSnapshotDTO
    *   `enemies`: list[ActorSnapshotDTO]
    *   `current_target`: ActorSnapshotDTO | None
    *   `status`: "active" | "waiting" | "finished"
    *   `belt_items`: list[dict] (Предметы в поясе)
*   **CombatMoveDTO**:
    *   `attack_zones`: list[str]
    *   `block_zones`: list[str]
    *   `ability_key`: str | None
