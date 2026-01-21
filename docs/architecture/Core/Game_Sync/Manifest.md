# 🔄 Game Sync Service (Lazy State & Session Management)

> **Status:** ⚠️ Legacy / Needs Integration

## 🎯 Описание
Сервис "ленивой" синхронизации состояния персонажа.
Вместо постоянных фоновых процессов, он пересчитывает состояние (HP, Energy, Cooldowns) **только в момент обращения** к персонажу.

Также отвечает за управление жизненным циклом сессий (Бой, Инвентарь) через `GameStateOrchestrator`.

## ⚙️ Функционал
1.  **Lazy Regen:** Расчет восстановленного HP/Energy на основе `last_update_time`.
2.  **State Synchronization:** Обновление данных в Redis перед началом любой активности (Бой, Крафт).
3.  **Session Management:** Восстановление и бэкап сессий при входе/выходе.

## 📂 Структура (V2 Target)
*   [📄 Architecture_Session_State.md](./Architecture_Session_State.md) — **Целевая архитектура кэширования и сессий**.
*   **API:** `synchronize_state(char_id)`, `restore_full_state(char_id)`.
*   **Engine:** Regen Formulas.
*   **Integration:** `AccountManager` (Redis), `StatsAggregationService`.

## 🔗 Current Code
*   `apps/game_core/system/game_sync/game_sync_service.py`
*   `apps/game_core/modules/status/regen_service.py`
