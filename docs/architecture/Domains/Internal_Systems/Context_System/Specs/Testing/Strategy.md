# Context Assembler v2: Testing Strategy

## 🎯 Философия и Цели

**Основная цель:** Обеспечить стабильность критического компонента системы (Context Assembler), который отвечает за подготовку данных для боевой системы.

**Принципы:**
1.  **P0 First:** Сначала покрываем критические пути (Combat Flow) и обработку ошибок.
2.  **Isolation:** Юнит-тесты не должны зависеть от внешней инфраструктуры (Mock DB/Redis).
3.  **Realism:** Интеграционные тесты должны проверять контракты данных, максимально приближенные к боевым.

## 📊 Пирамида Тестирования

### 1. Unit Tests (60%)
Изолированная проверка логики сборки и трансформации данных.
*   **Scope:** `PlayerAssembler`, `MonsterAssembler`, `TempContext Schemas`.
*   **Mocking:** Полный мок БД (Repositories) и Redis.

### 2. Integration Tests (30%)
Проверка взаимодействия компонентов внутри сервиса.
*   **Scope:** `Orchestrator` -> `Assembler` -> `Redis Manager`.
*   **Focus:** Корректность форматов ключей Redis, обработка частичных сбоев.

### 3. E2E / Contract Tests (10%)
Проверка, что собранный контекст пригоден для потребления Combat Service.
*   **Scope:** `Context Request` -> `Redis Data` -> `Combat Service Validation`.

## 🚦 Приоритеты (Roadmap)

| Priority | Component | Type | Status |
|----------|-----------|------|--------|
| **P0** | **Combat Flow Integration** | Integration | 🔴 Todo |
| **P0** | **Redis Error Handling** | Unit/Int | 🔴 Todo |
| **P0** | **Schema Validation (No Core Fields)** | Unit | 🔴 Todo |
| P1 | PlayerAssembler Logic | Unit | 🔴 Todo |
| P1 | MonsterAssembler Logic | Unit | 🔴 Todo |
| P2 | Performance Benchmarks | Perf | 🔴 Todo |

## 📂 Структура Документации

*   [Unit Testing Specs](./unit/README.md)
*   [Integration Testing Specs](./integration/README.md)
*   [Fixtures & Mocks](./fixtures/README.md)
