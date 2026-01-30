# 📋 PROJECT TODO LIST & TECHNICAL DEBT

Этот документ сгенерирован автоматически на основе анализа кодовой базы (grep "TODO").
Дата генерации: 2023-10-27
Дата обновления: 2023-10-27 (AI Update)

---

## 🚨 HIGH PRIORITY (CRITICAL PATH)

Эти задачи блокируют основной игровой цикл или являются критическими багами.

### 1. Onboarding & Scenario Transition
*   **Status:** 🟡 IN PROGRESS
*   **Context:** Переход игрока из регистрации в игровой мир.
*   **Tasks:**
    *   `docs/architecture/Domains/User_Features/Account/API/Onboarding.md`: Payload для Scenario пустой (Код реализован, нужно обновить доку).
    *   `src/backend/domains/user_features/combat/orchestrators/handler/combat_session_service.py`: Добавить переходы состояний (COMBAT -> EXPLORATION/LOBBY).

### 2. Combat Engine Stability
*   **Status:** 🟡 WARNING
*   **Context:** Ядро боевой системы.
*   **Tasks:**
    *   `src/backend/domains/user_features/combat/combat_engine/processors/collector.py`: Добавить проверку размера очереди `q:actions` (защита от флуда).
    *   `src/backend/domains/user_features/combat/combat_engine/workers/tasks/victory_finalizer_task.py`: Реализовать логику финализации боя (раздача наград, опыт).

---

## 🛠️ BACKEND DEVELOPMENT

### 🛡️ Context System & Assemblers
*   `src/backend/domains/internal_systems/context_assembler/logic/monster_assembler.py`: Рефакторинг `ContextRedisManager` (удалить атрибут `.redis`).
*   `src/backend/domains/internal_systems/context_assembler/schemas/combat.py`: Реализовать сбор абилок из Character/Skills/Items.
*   `src/backend/domains/internal_systems/context_assembler/schemas/inventory.py`: Рассчитать реальный вес инвентаря.

### 🎒 Inventory Domain
*   `src/backend/domains/user_features/inventory/engine/dispatcher_bridge.py`: Реализовать вызов `EffectsEngine`.
*   `src/backend/domains/user_features/inventory/services/inventory_service.py`: Обработка ошибки "Item not found".

### 🗺️ Exploration & Scenario
*   `src/backend/domains/user_features/exploration/services/exploration_service.py`: Реализовать пагинацию.
*   `src/backend/domains/user_features/exploration/engine/dispatcher_bridge.py`: Интеграция с доменами Loot, Monster, NPC/Dialog (когда они будут готовы).
*   `src/backend/domains/user_features/scenario/service/session_service.py`: Заменить прямые вызовы Repo на ARQ задачи (асинхронный бэкап).

---

## 🖥️ FRONTEND (TELEGRAM BOT)

*   `src/frontend/telegram_bot/features/combat/system/components/flow_ui.py`: Реализовать отображение наград.
*   `src/frontend/telegram_bot/features/combat/system/components/content_ui.py`: Получение списка абилок и предметов пояса из DTO.
*   `src/frontend/telegram_bot/base/base_orchestrator.py`: Реализовать метод `render_menu` в Director.
*   `src/frontend/telegram_bot/features/inventory/system/inventory_bot_orchestrator.py`: Обработка ошибок (редирект на логин?).

---

## 🧪 TESTING & QA

*   **Redis Error Handling:** 🔴 Todo (P0)
*   **Combat Flow Integration:** 🔴 Todo (P0)
*   **Schema Validation:** 🔴 Todo (P0)
*   **Player/Monster Assembler Logic:** 🔴 Todo (P1)
*   **Performance Benchmarks:** 🔴 Todo (P2)

---

## 🧹 REFACTORING & CLEANUP

*   **Type Safety:** `executor.py` все еще содержит `type: ignore`.
*   **Hardcoded Values:**
    *   `Gear Score` (заглушка 100).
    *   `MAX_HAND_SIZE` (константа 3).
*   **Architecture:**
    *   `src/backend/domains/user_features/exploration/api/router.py`: Рефакторинг Gateway (возврат `CoreResponseDTO`).
    *   `src/frontend/bot/ui_service/status_menu/status_service.py`: Заменить прямые вызовы репозиториев на `StatusClient`.

---

## 🤖 AI SUMMARY & ESTIMATION

**Общее состояние:** Проект находится в стадии активной разработки (Alpha/MVP). Основной каркас (Clean Architecture) соблюдается.

**Прогресс:**
*   ✅ **Onboarding Finalization:** Реализован переход в Scenario через SystemDispatcher.
*   ✅ **Stats System:** Внедрен `StatKey` Enum, обновлены формулы и DTO.
*   ✅ **Type Safety:** Устранены основные проблемы с типизацией в `AbilityService` и `StatsEngine`.

**Ключевые риски:**
1.  **Связность доменов:** Inventory и Exploration сильно зависят от еще не реализованных частей (Loot, NPC).
2.  **Тесты:** Критически не хватает интеграционных тестов для Redis и боевого цикла.

**Рекомендация:**
Сфокусироваться на **Task 2 (Combat Finalizer)**, чтобы замкнуть игровой цикл (Регистрация -> Мир -> Бой -> Награда -> Мир). Остальное — полировка.