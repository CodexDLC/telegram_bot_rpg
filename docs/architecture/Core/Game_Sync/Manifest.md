# 🔄 Game Sync Service (Lazy State)

> **Status:** ⚠️ Legacy / Needs Integration

## 🎯 Описание
Сервис "ленивой" синхронизации состояния персонажа.
Вместо постоянных фоновых процессов, он пересчитывает состояние (HP, Energy, Cooldowns) **только в момент обращения** к персонажу.

## ⚙️ Функционал
1.  **Lazy Regen:** Расчет восстановленного HP/Energy на основе `last_update_time`.
2.  **State Synchronization:** Обновление данных в Redis перед началом любой активности (Бой, Крафт).
3.  **Quick Heal:** Логика быстрого восстановления (для анимаций отдыха).

## 📂 Структура (V2 Target)
*   **API:** `synchronize_state(char_id)`.
*   **Engine:** Regen Formulas.
*   **Integration:** `AccountManager` (Redis), `StatsAggregationService`.

## 🔗 Current Code
*   `apps/game_core/system/game_sync/game_sync_service.py`
*   `apps/game_core/modules/status/regen_service.py`
