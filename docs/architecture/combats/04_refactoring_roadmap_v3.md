# Refactoring Roadmap (RBC v3.0)

Этот документ фиксирует пошаговый план перехода на архитектуру RBC v3.0.
**Принцип работы:** Step-by-Step. Обсуждаем этап -> Реализуем -> Переходим к следующему.

---

## 🏛️ Architectural Layers (The Rule)
Четкое разделение ответственности между слоями:

1.  **Infrastructure Layer (`apps.common`)**
    *   **Service:** `CombatManager`.
    *   **Responsibility:** Низкоуровневая работа с Redis. Знает про ключи (`RedisKeys`), пайплайны, Lua-скрипты.
    *   **Data:** Оперирует сырыми данными (`dict`, `list`, `bytes`). Не знает про сложные DTO бизнес-логики.
    *   **Rule:** Никакой бизнес-логики. Только "Сохранить", "Загрузить", "Атомарно изменить".

2.  **Domain Layer (`apps.game_core`)**
    *   **Services:** `CombatDataService`, `CombatSessionService`, `CombatLifecycleService`.
    *   **Responsibility:** Бизнес-логика, оркестрация, валидация.
    *   **Data:** Оперирует DTO (`BattleContext`, `ActorSnapshot`).
    *   **Rule:** Не лезет в Redis напрямую. Использует `CombatManager`.

---

## 🗺️ Phase 1: Foundation (Data & Math)
*Цель: Подготовить структуры данных и чистую математику, не зависящую от Redis/ARQ.*

### Step 1.1: DTO Update
*   **File:** `apps/common/schemas_dto/combat_source_dto.py`
*   **Task:** Привести DTO в полное соответствие с `02_combat_dtos_spec.md`.
*   **Changes:**
    *   Обновить `ActorSnapshot` (добавить `xp_buffer`, `dirty_stats`).
    *   Обновить `ActiveAbilityDTO` (замена старых эффектов).
    *   Проверить `CombatMoveDTO` и `InteractionResultDTO`.

### Step 1.2: Combat Calculator (Pure Math)
*   **File:** `apps/game_core/modules/combat/core/combat_calculator.py`
*   **Task:** Создать статический калькулятор.
*   **Logic:**
    *   Принимает статы и флаги.
    *   Считает попадание, крит, блок.
    *   Возвращает цифры урона и флаги событий.
    *   *Никакого изменения стейта.*

---

## ⚙️ Phase 2: Logic Services (State Mutation)
*Цель: Реализовать логику изменения стейта и управления эффектами.*

### Step 2.1: Mechanics Service
*   **File:** `apps/game_core/modules/combat/services/mechanics_service.py`
*   **Task:** Реализовать мутацию `ActorSnapshot`.
*   **Logic:**
    *   `apply_damage_result`: HP/EN update, Token update.
    *   `register_xp`: Запись в `xp_buffer`.
    *   `pay_cost`: Списание ресурсов.

### Step 2.2: Ability Service
*   **File:** `apps/game_core/modules/combat/services/ability_service.py`
*   **Task:** Управление жизненным циклом абилок.
*   **Logic:**
    *   `pre_calculate`: Выдача флагов (ignore_block, etc).
    *   `post_calculate`: Триггеры (on_hit).
    *   `apply_ability`: Создание записи в `active_abilities` + инъекция в `temp` статы.

---

## 🎷 Phase 3: The Pipeline (Orchestration)
*Цель: Связать сервисы в единый процесс обработки одного действия.*

### Step 3.1: Pipeline Orchestrator
*   **File:** `apps/game_core/modules/combat/pipeline/orchestrator.py`
*   **Task:** Реализовать метод `process_action(ctx, action)`.
*   **Flow:**
    1.  **Prep:** `AbilityService.check_cost` -> `AbilityService.pre_calc`.
    2.  **Calc:** `CombatCalculator.calculate`.
    3.  **Post:** `AbilityService.post_calc`.
    4.  **Apply:** `MechanicsService.apply`.

---

## 👷 Phase 4: The Workers (Async Engine)
*Цель: Реализовать асинхронную обработку очередей.*

### Step 4.1: Combat Executor (The Muscle)
*   **File:** `apps/game_core/modules/combat/workers/combat_executor.py`
*   **Task:** Обработка батчей задач.
*   **Logic:**
    *   Locking (`sys:busy`).
    *   Loading Context (`ActorManager`).
    *   Loop -> `PipelineOrchestrator`.
    *   Atomic Commit.

### Step 4.2: Combat Manager (The Collector)
*   **File:** `apps/game_core/modules/combat/workers/combat_manager.py`
*   **Task:** Матчмейкинг и обработка сигналов.
*   **Logic:**
    *   `process_signal(check_immediate)`: Поиск пары в Redis.
    *   `process_signal(check_timeout)`: Превращение в Forced Action.
    *   Dispatch -> `arq.enqueue(executor)`.

### Step 4.3: ARQ Tasks
*   **File:** `apps/common/services/arq/tasks/combat_tasks.py`
*   **Task:** Регистрация задач для воркеров.

---

## 🚪 Phase 5: Gateway (Entry & API)
*Цель: Заменить старые оркестраторы единой точкой входа.*

### Step 5.1: Combat Gateway
*   **File:** `apps/game_core/modules/combat/combat_gateway.py`
*   **Task:** Консолидация `TurnOrchestrator` и `InteractionOrchestrator`.
*   **Methods:**
    1.  `submit_move(char_id, action)`: Валидация -> Redis Write -> Signal.
    2.  `get_state(char_id)`: Чтение Snapshot/Logs.
    3.  `system_call(...)`: Внутренние вызовы.

### Step 5.2: Cleanup
*   **Task:** Удаление старых файлов (`combat_turn_orchestrator.py`, `combat_interaction_orchestrator.py`).

---

## 📝 Status Log
*   [ ] Phase 1.1: DTO Update
*   [ ] Phase 1.2: Calculator
*   [ ] Phase 2.1: Mechanics
*   [ ] Phase 2.2: Ability
*   [ ] Phase 3.1: Pipeline
*   [ ] Phase 4.1: Executor
*   [ ] Phase 4.2: Manager
*   [ ] Phase 5.1: Gateway
