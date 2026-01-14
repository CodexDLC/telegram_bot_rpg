# 🧪 Task: Combat Testing Strategy & Documentation

[⬅️ Назад: Roadmap](../Roadmap.md)

---

## 🎯 Цель
Разработать и задокументировать стратегию тестирования для Combat Domain, используя `Context Assembler` как эталон.
Боевая система критична к ошибкам (математика, состояния), поэтому требует строгого подхода к покрытию тестами.

## 📋 Подзадачи (Subtasks)

### 1. 📐 Strategy Definition (Стратегия)
- [x] Создать `docs/architecture/Domains/User_Features/Combat/Specs/Testing/Strategy.md`.
    - [x] Определить Пирамиду тестирования (Unit vs Integration).
    - [x] Определить принципы (Stateless Math, Mocked State).

### 2. 📦 Unit Testing Specs (Юнит-тесты)
- [x] Создать `docs/architecture/Domains/User_Features/Combat/Specs/Testing/Unit/README.md`.
    - [x] **Resolver:** Проверка формул (Accuracy, Crit, Damage) на фиксированных инпутах.
    - [x] **ContextBuilder:** Проверка сборки флагов из интентов.
    - [x] **AbilityService:** Проверка логики эффектов и списания ресурсов (без БД).
    - [x] **FeintService:** Проверка логики колоды и руки.

### 3. 🔗 Integration Testing Specs (Интеграция)
- [x] Создать `docs/architecture/Domains/User_Features/Combat/Specs/Testing/Integration/README.md`.
    - [x] **Pipeline Flow:** Проверка полного цикла `calculate()` (от `ContextBuilder` до `Mechanics`).
    - [x] **Executor Loop:** Проверка обработки очередей и Dual Wield логики.

### 4. 🎭 Fixtures & Mocks (Фикстуры)
- [x] Создать `docs/architecture/Domains/User_Features/Combat/Specs/Testing/Fixtures/README.md`.
    - [x] Описать структуру моков: `MockActorSnapshot`, `MockCombatMove`, `MockBattleContext`.
    - [x] Определить эталонные JSON-сценарии (Golden Files) для проверки регрессии.

## 🔗 Референсы
*   `docs/architecture/Core/Context_System/Specs/Testing/Strategy.md` (Эталон)
