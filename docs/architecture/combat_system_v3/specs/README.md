# RBC v3.1 Specifications

⬅️ [Назад](../README.md) | 🏠 [Документация](../../../README.md)

## 📂 Data Structures
*   [**DTOs**](./data_structures/dtos.md) — Объекты передачи данных.
*   [**Redis Schema**](./data_structures/redis_schema.md) — Структура хранения в Redis.
*   [**Actor Model**](./data_structures/actor_model.md) — Модель персонажа (State, Raw, Snapshot).

## 📂 Components
*   [**Initialization**](./components/initialization.md) — Создание боя.
*   [**TurnManager**](./components/turn_manager.md) — Прием ходов.
*   [**Collector**](./components/collector_processor.md) — Матчмейкинг.
*   [**Executor**](./components/executor.md) — Оркестрация.
*   [**Pipeline**](./components/pipeline.md) — Логика расчета.
*   [**CombatResolver**](./components/combat_resolver.md) — Математика.
*   [**AbilityService**](./components/ability_service.md) — Эффекты.
*   [**StatsEngine**](./components/stats_engine.md) — Калькулятор статов.

## 📂 Features
*   [**Chaos Protocol**](../concepts/chaos_protocol.md) — Мусорщик сессий.
*   [**Trigger System**](./components/features/trigger_system.md) — Система флагов и триггеров.
*   [**Feints Library**](./components/features/feints_library.md) — Библиотека финтов.

## 📂 Flows
*   [**API Flows**](./flows/api_flow.md) — Синхронные процессы.
*   [**Worker Flows**](./flows/worker_flow.md) — Асинхронные процессы.
