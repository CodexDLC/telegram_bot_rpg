# Component: CombatDataService

⬅️ [Назад](../../README.md) | 🏠 [Документация](../../../../../README.md)

**File:** `apps/game_core/modules/combat/combat_engine/combat_data_service.py`
**Layer:** Engine Data Layer (Worker Side).
**Responsibility:** Фасад над `CombatManager` для Воркеров (Collector, Executor). Преобразует сырые данные Redis в DTO.

## 1. Методы для Коллектора (Lightweight)
*   `get_battle_meta`: Загружает метаданные.
*   `get_intent_moves`: Загружает намерения игроков.
*   `get_targets`: Загружает очереди целей.
*   `transfer_actions`: Переносит мувы в очередь исполнения.

## 2. Методы для Исполнителя (Heavyweight)
*   `load_battle_context`:
    1.  Загружает полные данные всех участников через `CombatManager`.
    2.  Собирает `ActorSnapshot` (парсит JSON, маппит поля).
    3.  Возвращает готовый `BattleContext`.
*   `commit_session`:
    1.  Собирает изменения из `BattleContext` (State, XP, Logs).
    2.  Формирует пакет обновлений.
    3.  Сохраняет в Redis через `CombatManager`.

## 3. Helpers
*   `_build_snapshot`: Сборка объекта Актера из разрозненных кусков (State, Raw, Loadout).
