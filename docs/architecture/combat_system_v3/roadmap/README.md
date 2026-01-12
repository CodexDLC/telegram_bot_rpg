# 🗺️ Combat System v3 Roadmap

⬅️ [Назад](../README.md) | 🏠 [Документация](../../../../README.md)

**Цель:** Полный перезапуск боевой системы (RBC v3) с новой архитектурой данных и пайплайном.

---

## ✅ Phase 1: Data & Core (Completed)
Фундамент системы. Структуры данных и базовые алгоритмы.

*   [x] **DTOs Refactoring (v3.1):**
    *   `ActorSnapshot` (Redis Mirror).
    *   `ActorStats` (Composition: Mods + Skills).
    *   `CombatModifiersDTO` (Cleaned up).
*   [x] **Redis Schema:**
    *   Unified Actor JSON (`actor:{id}`).
    *   Moves Buffer (`moves:{id}`).
*   [x] **Context Assembler (v2):**
    *   Mapping DB -> Redis JSON.
    *   Support for new Item/Skill structure.
*   [x] **Calculators:**
    *   `StatsWaterfallCalculator` (Updated for `source/temp`).
    *   `CombatResolver` (Updated for `ActorStats` composition).
*   [x] **Infrastructure:**
    *   `CombatGateway`, `CombatSessionService`, `CombatTurnManager` (Ready v3.0).
    *   `CombatCollector` (Ready v3.0).

---

## 🚧 Phase 2: Pipeline & Execution (Critical Path)
Реализация отсутствующей бизнес-логики.

*   [ ] **Combat Pipeline (New):**
    *   Создать `apps/game_core/modules/combat/combat_engine/logic/combat_pipeline.py`.
    *   Реализовать фазы:
        1.  **Context Build:** Сборка `PipelineContextDTO`.
        2.  **Ability (Pre):** Обработка баффов/дебаффов.
        3.  **Stats Engine:** Расчет `ActorStats` через Waterfall.
        4.  **Resolver:** Вызов `CombatResolver`.
        5.  **Mechanics:** Применение результатов.
*   [ ] **Combat Executor (Update):**
    *   Интегрировать `CombatPipeline` в `CombatExecutor`.
    *   Реализовать ветвление (Exchange vs Instant).
*   [ ] **Services Implementation:**
    *   `AbilityService`: Логика эффектов (Poison, Stun).
    *   `MechanicsService`: Логика урона, смерти, XP.
    *   `StatsEngine`: Адаптер для Waterfall Calculator.

---

## 📅 Phase 3: Content & Balance (Planned)
Наполнение системы контентом.

*   [ ] **Skills Implementation:**
    *   Реализация формул для всех скиллов (Swords, Heavy Armor...).
*   [ ] **Abilities Implementation:**
    *   Active Skills (Fireball, Heal).
    *   Passive Traits.
*   [ ] **AI Logic:**
    *   Behavior Trees / Utility AI.

---

## 📂 Files to Implement (Next Steps)

### 1. Logic Core
*   `apps/game_core/modules/combat/combat_engine/logic/combat_pipeline.py` (NEW)
*   `apps/game_core/modules/combat/combat_engine/logic/stats_engine.py` (NEW)

### 2. Services
*   `apps/game_core/modules/combat/services/ability_service.py` (NEW)
*   `apps/game_core/modules/combat/services/mechanics_service.py` (NEW)

### 3. Integration
*   `apps/game_core/modules/combat/combat_engine/processors/executor.py` (UPDATE)
