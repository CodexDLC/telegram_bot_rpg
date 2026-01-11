# Component: CombatGateway (Ingress API)

⬅️ [Назад](../README.md) | 🏠 [Документация](../../../../README.md)

**File:** `apps/game_core/modules/combat/combat_gateway.py`
**Layer:** API Layer (Runtime).
**Responsibility:** Единая точка входа для всех запросов к идущему бою.

## 1. System Contract (CoreRouter)
Метод `get_entry_point(action, context)` используется для межмодульного взаимодействия.

*   **Action:** `snapshot` -> Возвращает `CombatDashboardDTO`.
*   **Action:** `logs` -> Возвращает `CombatLogDTO`.
*   **Action:** `attack`, `use_item` -> Регистрирует ход.

## 2. Client Contract (API Wrapper)
Методы `handle_action` и `get_view` оборачивают результат в `CoreResponseDTO`.
Это нужно для унификации ответов API (чтобы фронтенд всегда получал `header` с состоянием игры).

## 3. Логика Маршрутизации
Гейтвей не содержит бизнес-логики. Он делегирует все запросы в `CombatSessionService`.

*   **Read:** `session_service.get_snapshot(char_id)`.
*   **Write:** `session_service.register_move(char_id, payload)`.
